"""
Сервис генерации официальных корпоративных PDF-отчетов для проекта «Горизонт».
Использует библиотеку ReportLab для создания многостраничных отчетов
с поддержкой кириллицы, мультивалютных расчетов (BYN/USD),
таблиц сфер жизни, реестра целей и индексов гармонии.
"""

import io
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from sqlalchemy.orm import Session
from models import User, LifeSphere, GoalCard, ExchangeRateCache

# Глобальные переменные для шрифтов с поддержкой кириллицы
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
_FONTS_INITIALIZED = False


def init_pdf_fonts():
    """
    Поиск и регистрация системных TrueType шрифтов с поддержкой кириллицы (Arial, DejaVuSans, LiberationSans).
    """
    global FONT_REGULAR, FONT_BOLD, _FONTS_INITIALIZED
    if _FONTS_INITIALIZED or not HAS_REPORTLAB:
        return

    candidates = [
        # Windows Fonts
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
        (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf"),
        (r"C:\Windows\Fonts\segui.ttf", r"C:\Windows\Fonts\seguib.ttf"),
        # Linux / Docker Fonts
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"),
    ]

    for reg_path, bold_path in candidates:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont("HorizonFont", reg_path))
                b_path = bold_path if os.path.exists(bold_path) else reg_path
                pdfmetrics.registerFont(TTFont("HorizonFont-Bold", b_path))
                FONT_REGULAR = "HorizonFont"
                FONT_BOLD = "HorizonFont-Bold"
                _FONTS_INITIALIZED = True
                return
            except Exception as e:
                print(f"⚠️ Не удалось зарегистрировать шрифт {reg_path}: {e}")
                continue

    _FONTS_INITIALIZED = True


class NumberedCanvas(canvas.Canvas):
    """
    Двухпроходный канвас для корректного отображения колонтитулов и 'Страница X из Y'.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        self.saveState()
        self.setFont(FONT_REGULAR, 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Верхний колонтитул на страницах начиная со второй
        if self._pageNumber > 1:
            self.drawString(40, 808, "ГОРИЗОНТ | Аналитический отчет жизненного баланса и целей")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(40, 802, 555, 802)

        # Нижний колонтитул на всех страницах
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 38, 555, 38)

        self.drawString(40, 26, "Система «Горизонт» • Конфиденциальный аналитический отчет • horizon.app")
        page_str = f"Страница {self._pageNumber} из {total_pages}"
        self.drawRightString(555, 26, page_str)
        self.restoreState()


def get_latest_exchange_rate(db: Session) -> Decimal:
    """
    Получение курса USD/BYN из БД или дефолтного значения 2.9543.
    """
    cached = db.query(ExchangeRateCache).filter(ExchangeRateCache.currency_code == "USD").first()
    if cached and cached.rate:
        return Decimal(str(cached.rate))
    return Decimal("2.9543")


def calculate_harmony_index(spheres: List[LifeSphere]) -> int:
    """
    Расчет процента гармонии колеса баланса (от 10% до 100%).
    """
    if not spheres:
        return 80
    scores = [float(s.current_score) for s in spheres]
    mean = sum(scores) / len(scores)
    if mean == 0:
        return 50
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
    raw_harmony = 1.0 - (std_dev / 5.0)
    percent = max(10, min(100, int(round(raw_harmony * 100))))
    return percent


def generate_horizon_pdf_report(db: Session, user: User) -> bytes:
    """
    Генерация PDF-документа отчета с итогами по колесу баланса и целям текущего пользователя.
    Возвращает байты сгенерированного PDF.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("Библиотека reportlab не установлена на сервере.")

    init_pdf_fonts()

    # Сбор данных
    spheres = db.query(LifeSphere).filter(LifeSphere.user_id == user.id).order_by(LifeSphere.sort_order.asc()).all()
    for s in spheres:
        s.recalculate_score()
    db.commit()

    goals = db.query(GoalCard).filter(GoalCard.user_id == user.id).order_by(GoalCard.deadline.asc().nullslast()).all()
    fx_rate = get_latest_exchange_rate(db)

    # Расчет показателей
    harmony_pct = calculate_harmony_index(spheres)
    avg_score = (sum(float(s.current_score) for s in spheres) / len(spheres)) if spheres else 0.0

    total_goals = len(goals)
    in_progress_count = sum(1 for g in goals if g.status == "in_progress")
    achieved_count = sum(1 for g in goals if g.status == "achieved")
    draft_count = sum(1 for g in goals if g.status == "draft")

    # Мультивалютный подсчет бюджетов
    total_byn = Decimal("0.00")
    total_usd = Decimal("0.00")
    for g in goals:
        amt = Decimal(str(g.cost_amount or 0.0))
        cur = (g.currency or "BYN").upper()
        if cur == "BYN":
            total_byn += amt
            total_usd += amt / fx_rate
        else:
            total_usd += amt
            total_byn += amt * fx_rate

    # Настройка документа
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Стили текста
    style_brand = ParagraphStyle(
        "BrandTitle",
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A73E8")
    )
    style_subtitle = ParagraphStyle(
        "BrandSubtitle",
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5F6368")
    )
    style_meta_label = ParagraphStyle(
        "MetaLabel",
        fontName=FONT_BOLD,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
        alignment=2 # Right align
    )
    style_meta_val = ParagraphStyle(
        "MetaVal",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        alignment=2
    )
    style_section_heading = ParagraphStyle(
        "SectionHeading",
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )
    style_cell_normal = ParagraphStyle(
        "CellNormal",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )
    style_cell_bold = ParagraphStyle(
        "CellBold",
        fontName=FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )
    style_cell_center = ParagraphStyle(
        "CellCenter",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
        alignment=1 # Center
    )
    style_cell_right = ParagraphStyle(
        "CellRight",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
        alignment=2 # Right
    )
    style_th = ParagraphStyle(
        "TableHeader",
        fontName=FONT_BOLD,
        fontSize=8,
        leading=11,
        textColor=colors.white,
        alignment=1
    )

    story = []

    # =========================================================================
    # 1. ШАПКА ДОКУМЕНТА (БРЕНДИНГ И МЕТАДАННЫЕ)
    # =========================================================================
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    user_name = user.full_name or user.login
    user_role = "Администратор (Admin)" if user.role == "admin" else "Пользователь (User)"

    header_left = [
        Paragraph("ГОРИЗОНТ", style_brand),
        Paragraph("Карта желаний, колесо баланса &amp; декомпозиция целей", style_subtitle),
        Paragraph("Официальный аналитический отчет резидента", style_subtitle)
    ]
    header_right = [
        Paragraph(f"<b>Резидент:</b> {user_name} ({user.login})", style_meta_val),
        Paragraph(f"<b>Email:</b> {user.email}", style_meta_val),
        Paragraph(f"<b>Роль в системе:</b> {user_role}", style_meta_val),
        Paragraph(f"<b>Дата отчета:</b> {now_str}", style_meta_val),
        Paragraph(f"<b>Официальный курс:</b> 1 USD = {fx_rate:.4f} BYN (НБРБ)", style_meta_val),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[270, 253])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A73E8"), spaceAfter=10))

    # =========================================================================
    # 2. СВОДНЫЕ KPI КАРТОЧКИ (ИНДЕКС ГАРМОНИИ, БАЛЛ, ЦЕЛИ, БЮДЖЕТ)
    # =========================================================================
    if harmony_pct >= 80:
        harmony_status = "Высокая гармония"
        h_color = "#10B981"
    elif harmony_pct >= 60:
        harmony_status = "Умеренный баланс"
        h_color = "#3B82F6"
    else:
        harmony_status = "Обнаружен перекос"
        h_color = "#F59E0B"

    kpi_card_1 = [
        Paragraph("<b>ИНДЕКС ГАРМОНИИ</b>", ParagraphStyle("KPIHead1", fontName=FONT_BOLD, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1)),
        Spacer(1, 2),
        Paragraph(f"<font color='{h_color}'><b>{harmony_pct}%</b></font>", ParagraphStyle("KPIVal1", fontName=FONT_BOLD, fontSize=16, leading=18, alignment=1)),
        Spacer(1, 1),
        Paragraph(harmony_status, ParagraphStyle("KPISub1", fontName=FONT_REGULAR, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1))
    ]

    kpi_card_2 = [
        Paragraph("<b>СФЕР ЖИЗНИ</b>", ParagraphStyle("KPIHead2", fontName=FONT_BOLD, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1)),
        Spacer(1, 2),
        Paragraph(f"<b>{len(spheres)} сфер</b>", ParagraphStyle("KPIVal2", fontName=FONT_BOLD, fontSize=16, leading=18, textColor=colors.HexColor("#1E293B"), alignment=1)),
        Spacer(1, 1),
        Paragraph(f"Средний балл: <b>{avg_score:.1f}</b> из 10", ParagraphStyle("KPISub2", fontName=FONT_REGULAR, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1))
    ]

    kpi_card_3 = [
        Paragraph("<b>РЕЕСТР ЦЕЛЕЙ</b>", ParagraphStyle("KPIHead3", fontName=FONT_BOLD, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1)),
        Spacer(1, 2),
        Paragraph(f"<b>{total_goals} целей</b>", ParagraphStyle("KPIVal3", fontName=FONT_BOLD, fontSize=16, leading=18, textColor=colors.HexColor("#1E293B"), alignment=1)),
        Spacer(1, 1),
        Paragraph(f"В работе: <b>{in_progress_count}</b> • Готово: <b>{achieved_count}</b>", ParagraphStyle("KPISub3", fontName=FONT_REGULAR, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1))
    ]

    kpi_card_4 = [
        Paragraph("<b>ИТОГОВЫЙ БЮДЖЕТ</b>", ParagraphStyle("KPIHead4", fontName=FONT_BOLD, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1)),
        Spacer(1, 2),
        Paragraph(f"<b>{int(round(total_byn)):,} Br</b>".replace(",", " "), ParagraphStyle("KPIVal4", fontName=FONT_BOLD, fontSize=16, leading=18, textColor=colors.HexColor("#0D9488"), alignment=1)),
        Spacer(1, 1),
        Paragraph(f"Эквивалент: <b>${int(round(total_usd)):,} USD</b>".replace(",", " "), ParagraphStyle("KPISub4", fontName=FONT_REGULAR, fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1))
    ]

    kpi_table = Table([[kpi_card_1, kpi_card_2, kpi_card_3, kpi_card_4]], colWidths=[127, 127, 127, 142])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # =========================================================================
    # 3. ТАБЛИЦА: СФЕРЫ ЖИЗНИ И ТЕКУЩИЙ БАЛАНС
    # =========================================================================
    story.append(Paragraph("1. Справочник сфер жизни и оценка баланса", style_section_heading))

    sphere_goals_count = {}
    for g in goals:
        s_id = str(g.sphere_id)
        sphere_goals_count[s_id] = sphere_goals_count.get(s_id, 0) + 1

    sphere_rows = [[
        Paragraph("#", style_th),
        Paragraph("Сфера жизни", ParagraphStyle("THLeft", parent=style_th, alignment=0)),
        Paragraph("Текущий балл", style_th),
        Paragraph("Целевой балл", style_th),
        Paragraph("Прогресс", style_th),
        Paragraph("Целей", style_th),
        Paragraph("Статус сферы", style_th),
    ]]

    for idx, s in enumerate(spheres, start=1):
        c_score = float(s.current_score)
        t_score = float(s.target_score) or 10.0
        pct = min(100, int(round((c_score / t_score) * 100))) if t_score > 0 else 0
        cnt = sphere_goals_count.get(str(s.id), 0)

        if pct >= 80:
            status_text = "<font color='#10B981'><b>Гармонично</b></font>"
        elif pct >= 50:
            status_text = "<font color='#3B82F6'>В динамике</font>"
        else:
            status_text = "<font color='#F59E0B'>Требует фокуса</font>"

        sphere_rows.append([
            Paragraph(str(idx), style_cell_center),
            Paragraph(f"<b>{s.title}</b>", style_cell_normal),
            Paragraph(f"{c_score:.1f}", style_cell_center),
            Paragraph(f"{t_score:.1f}", style_cell_center),
            Paragraph(f"{pct}%", style_cell_center),
            Paragraph(str(cnt), style_cell_center),
            Paragraph(status_text, style_cell_center),
        ])

    # Итоговая строка
    sphere_rows.append([
        Paragraph("", style_cell_center),
        Paragraph("<b>ИТОГО / СРЕДНЕЕ</b>", style_cell_bold),
        Paragraph(f"<b>{avg_score:.1f}</b>", style_cell_center),
        Paragraph("<b>10.0</b>", style_cell_center),
        Paragraph(f"<b>{min(100, int(round(avg_score * 10)))}%</b>", style_cell_center),
        Paragraph(f"<b>{total_goals}</b>", style_cell_center),
        Paragraph(f"<b>Гармония: {harmony_pct}%</b>", style_cell_center),
    ])

    spheres_table = Table(sphere_rows, colWidths=[24, 150, 64, 64, 60, 50, 111])
    spheres_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A73E8")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
        ('LINEBELOW', (0, -1), (-1, -1), 1.2, colors.HexColor("#CBD5E1")),
    ]))
    story.append(spheres_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 4. ТАБЛИЦА: РЕЕСТР ЦЕЛЕЙ И МУЛЬТИВАЛЮТНЫЙ БЮДЖЕТ (Br / USD)
    # =========================================================================
    story.append(Paragraph("2. Реестр целей и финансовая декомпозиция", style_section_heading))

    sphere_title_map = {str(s.id): s.title for s in spheres}

    priority_map = {
        "critical": "Критич.",
        "high": "Высокий",
        "medium": "Средний",
        "low": "Низкий"
    }

    status_map = {
        "in_progress": "В работе",
        "achieved": "Готово",
        "draft": "Черновик",
        "archived": "Архив"
    }

    goals_rows = [[
        Paragraph("#", style_th),
        Paragraph("Название цели", ParagraphStyle("THGoalLeft", parent=style_th, alignment=0)),
        Paragraph("Сфера жизни", ParagraphStyle("THSphereLeft", parent=style_th, alignment=0)),
        Paragraph("Приоритет", style_th),
        Paragraph("Статус", style_th),
        Paragraph("Прогресс", style_th),
        Paragraph("Дедлайн", style_th),
        Paragraph("Сумма (Br)", ParagraphStyle("THBynRight", parent=style_th, alignment=2)),
        Paragraph("Сумма ($)", ParagraphStyle("THUsdRight", parent=style_th, alignment=2)),
    ]]

    for idx, g in enumerate(goals, start=1):
        s_title = sphere_title_map.get(str(g.sphere_id), "Сфера")
        prio_text = priority_map.get(g.priority, g.priority or "Средний")
        stat_text = status_map.get(g.status, g.status or "В работе")
        
        amt = Decimal(str(g.cost_amount or 0.0))
        cur = (g.currency or "BYN").upper()
        if cur == "BYN":
            byn_val = amt
            usd_val = amt / fx_rate
        else:
            usd_val = amt
            byn_val = amt * fx_rate

        deadline_str = g.deadline.strftime("%d.%m.%Y") if g.deadline else "—"

        status_styled = stat_text
        if g.status == "achieved":
            status_styled = "<font color='#10B981'><b>Готово</b></font>"
        elif g.status == "in_progress":
            status_styled = "<font color='#3B82F6'>В работе</font>"

        goals_rows.append([
            Paragraph(str(idx), style_cell_center),
            Paragraph(f"<b>{g.title}</b>", style_cell_normal),
            Paragraph(s_title, style_cell_normal),
            Paragraph(prio_text, style_cell_center),
            Paragraph(status_styled, style_cell_center),
            Paragraph(f"{g.progress_percent}%", style_cell_center),
            Paragraph(deadline_str, style_cell_center),
            Paragraph(f"{int(round(byn_val)):,} Br".replace(",", " "), style_cell_right),
            Paragraph(f"${int(round(usd_val)):,}".replace(",", " "), style_cell_right),
        ])

    # Итоговая строка по целям
    goals_rows.append([
        Paragraph("", style_cell_center),
        Paragraph("<b>ИТОГО ПО ВСЕМ ЦЕЛЯМ:</b>", style_cell_bold),
        Paragraph(f"<b>{total_goals} целей</b>", style_cell_normal),
        Paragraph("", style_cell_center),
        Paragraph("", style_cell_center),
        Paragraph("", style_cell_center),
        Paragraph("", style_cell_center),
        Paragraph(f"<b>{int(round(total_byn)):,} Br</b>".replace(",", " "), style_cell_right),
        Paragraph(f"<b>${int(round(total_usd)):,}</b>".replace(",", " "), style_cell_right),
    ])

    goals_table = Table(goals_rows, colWidths=[20, 138, 85, 48, 50, 42, 50, 45, 45])
    goals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
        ('LINEBELOW', (0, -1), (-1, -1), 1.2, colors.HexColor("#CBD5E1")),
    ]))
    story.append(goals_table)

    story.append(Spacer(1, 12))

    # =========================================================================
    # 5. СНОСКА И ЮРИДИЧЕСКИЙ БЛОК
    # =========================================================================
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        fontName=FONT_REGULAR,
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#94A3B8")
    )
    disclaimer_text = (
        "Документ сгенерирован программно в системе «Горизонт» на основе актуальных данных пользователя, "
        "базы целей, декомпозиций шагов и официального курса Нацбанка РБ (НБРБ). "
        "Отчет является персональным и конфиденциальным."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    # Сборка документа
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

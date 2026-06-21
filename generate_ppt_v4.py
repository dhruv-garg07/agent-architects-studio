"""
Persistent Context Infrastructure — PPT v4 Generator
Generates a 12-slide dark-themed presentation using python-pptx.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ============================================================
# DESIGN SYSTEM
# ============================================================

# Colors
BG_DARK       = RGBColor(0x0D, 0x0D, 0x1A)   # Deep navy-black
BG_CARD       = RGBColor(0x1A, 0x1A, 0x2E)   # Dark card
BG_CARD_ALT   = RGBColor(0x16, 0x16, 0x2A)   # Slightly darker card
PURPLE        = RGBColor(0x7C, 0x3A, 0xED)   # Context/memory layer
PURPLE_LIGHT  = RGBColor(0xA7, 0x8B, 0xFA)   # Purple text highlight
BLUE          = RGBColor(0x3B, 0x82, 0xF6)   # Agent/orchestration
GREEN         = RGBColor(0x10, 0xB9, 0x81)   # Knowledge layer
ORANGE        = RGBColor(0xF5, 0x9E, 0x0B)   # Infrastructure
RED_SOFT      = RGBColor(0xEF, 0x44, 0x44)   # Warning/problem
CYAN          = RGBColor(0x06, 0xB6, 0xD4)   # Retrieval layer
TEXT_PRIMARY   = RGBColor(0xF8, 0xFA, 0xFC)   # Near-white
TEXT_SECONDARY = RGBColor(0x94, 0xA3, 0xB8)   # Muted gray
TEXT_MUTED     = RGBColor(0x64, 0x74, 0x8B)   # Very muted
WHITE          = RGBColor(0xFF, 0xFF, 0xFF)
CARD_BORDER    = RGBColor(0x2D, 0x2D, 0x4A)  # Subtle border

# Slide dimensions (widescreen 16:9)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Font
FONT_HEADING = "Calibri"
FONT_BODY    = "Calibri"

# Margins
MARGIN_LEFT  = Inches(0.8)
MARGIN_RIGHT = Inches(0.8)
MARGIN_TOP   = Inches(0.5)
CONTENT_W    = Inches(11.733)  # 13.333 - 0.8*2


def set_slide_bg(slide, color):
    """Set solid background color for a slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, left, top, width, height, text, 
                font_size=14, font_color=TEXT_PRIMARY, bold=False, 
                alignment=PP_ALIGN.LEFT, font_name=FONT_BODY,
                anchor=MSO_ANCHOR.TOP):
    """Add a text box with styling."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    
    # Set vertical anchor
    try:
        tf.paragraphs[0].alignment = alignment
    except:
        pass
    
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    
    return txBox


def add_multiline_textbox(slide, left, top, width, height, lines,
                          font_size=14, font_color=TEXT_PRIMARY,
                          alignment=PP_ALIGN.LEFT, line_spacing=1.2,
                          font_name=FONT_BODY):
    """Add textbox with multiple paragraphs."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    
    for i, line_data in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        
        if isinstance(line_data, dict):
            p.text = line_data.get('text', '')
            p.font.size = Pt(line_data.get('size', font_size))
            p.font.color.rgb = line_data.get('color', font_color)
            p.font.bold = line_data.get('bold', False)
            p.font.name = line_data.get('font', font_name)
            p.alignment = line_data.get('align', alignment)
            if 'space_after' in line_data:
                p.space_after = Pt(line_data['space_after'])
            if 'space_before' in line_data:
                p.space_before = Pt(line_data['space_before'])
        else:
            p.text = line_data
            p.font.size = Pt(font_size)
            p.font.color.rgb = font_color
            p.font.name = font_name
            p.alignment = alignment
    
    return txBox


def add_rounded_rect(slide, left, top, width, height, fill_color, 
                     border_color=None, border_width=Pt(1)):
    """Add a rounded rectangle shape."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    
    if border_color:
        shape.line.fill.solid()
        shape.line.fill.fore_color.rgb = border_color
        shape.line.width = border_width
    else:
        shape.line.fill.background()
    
    # Reduce corner radius
    if hasattr(shape, 'adjustments') and len(shape.adjustments) > 0:
        shape.adjustments[0] = 0.05
    
    return shape


def add_rect(slide, left, top, width, height, fill_color, border_color=None):
    """Add a plain rectangle."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.fill.solid()
        shape.line.fill.fore_color.rgb = border_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_arrow_down(slide, center_x, top_y, size=Inches(0.3), color=TEXT_MUTED):
    """Add a downward arrow indicator."""
    add_textbox(slide, center_x - Inches(0.15), top_y, Inches(0.3), Inches(0.3),
                "▼", font_size=12, font_color=color, alignment=PP_ALIGN.CENTER)


def add_branding(slide, text="Aldenaire International"):
    """Add branding text in top-left."""
    add_textbox(slide, MARGIN_LEFT, Inches(0.3), Inches(3), Inches(0.3),
                text, font_size=10, font_color=TEXT_MUTED, 
                font_name=FONT_BODY)


def add_slide_number(slide, num, total=12):
    """Add slide number in bottom-right."""
    add_textbox(slide, Inches(12.2), Inches(7.0), Inches(0.8), Inches(0.3),
                f"{num}/{total}", font_size=9, font_color=TEXT_MUTED,
                alignment=PP_ALIGN.RIGHT)


# ============================================================
# PRESENTATION
# ============================================================

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H

# Use blank layout
blank_layout = prs.slide_layouts[6]  # Blank


# ============================================================
# SLIDE 1 — TITLE
# ============================================================

slide1 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide1, BG_DARK)

# Subtle decorative line at top
add_rect(slide1, Inches(0), Inches(0), SLIDE_W, Inches(0.04), PURPLE)

# Branding
add_textbox(slide1, Inches(5.4), Inches(2.2), Inches(3), Inches(0.3),
            "Aldenaire International", font_size=12, font_color=PURPLE_LIGHT,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Title
add_textbox(slide1, Inches(1.5), Inches(2.8), Inches(10.3), Inches(1.5),
            "Building Persistent\nContext Infrastructure",
            font_size=44, font_color=TEXT_PRIMARY, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Subtitle
add_textbox(slide1, Inches(2.5), Inches(4.5), Inches(8.3), Inches(0.8),
            "A memory infrastructure that enables AI systems to continuously\nlearn and personalize experiences for every user.",
            font_size=16, font_color=TEXT_SECONDARY,
            alignment=PP_ALIGN.CENTER)

# Decorative accent bar
add_rect(slide1, Inches(5.9), Inches(5.5), Inches(1.5), Inches(0.03), PURPLE)

# Bottom line
add_textbox(slide1, Inches(4.5), Inches(6.0), Inches(4.3), Inches(0.4),
            "Architecture & System Design Review",
            font_size=13, font_color=TEXT_MUTED,
            alignment=PP_ALIGN.CENTER)

add_slide_number(slide1, 1)


# ============================================================
# SLIDE 2 — WHY TRADITIONAL AI SYSTEMS FAIL
# ============================================================

slide2 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide2, BG_DARK)
add_branding(slide2)

# Title
add_textbox(slide2, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Why Traditional AI Systems Fail",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

# Subtitle
add_textbox(slide2, MARGIN_LEFT, Inches(1.35), Inches(10), Inches(0.4),
            "Every AI system without persistent memory faces these fundamental limitations.",
            font_size=14, font_color=TEXT_SECONDARY)

# Three problem cards
card_w = Inches(3.6)
card_h = Inches(3.8)
card_top = Inches(2.3)
card_gap = Inches(0.35)
start_x = Inches(1.0)

problems = [
    {
        "icon": "🔴",
        "title": "No Long-Term Memory",
        "body": "Every session starts from zero. The LLM has no knowledge of past interactions, user preferences, or prior decisions.\n\nToken budgets are wasted re-establishing context that should already be known."
    },
    {
        "icon": "🔴", 
        "title": "Repeated Onboarding",
        "body": "Users must re-introduce themselves every session. Goals, preferences, and history are never retained.\n\nOnboarding cost multiplies across every touchpoint and every user."
    },
    {
        "icon": "🔴",
        "title": "Context Resets Every Session",
        "body": "Each new request discards all prior context. There is no accumulation of user understanding over time.\n\nPersonalization degrades. Token costs grow. AI accuracy remains static."
    }
]

for i, prob in enumerate(problems):
    x = start_x + i * (card_w + card_gap)
    
    # Card background
    add_rounded_rect(slide2, x, card_top, card_w, card_h, BG_CARD, CARD_BORDER)
    
    # Red accent bar at top of card
    add_rect(slide2, x + Inches(0.3), card_top + Inches(0.25), Inches(0.5), Inches(0.04), RED_SOFT)
    
    # Title
    add_textbox(slide2, x + Inches(0.3), card_top + Inches(0.5), card_w - Inches(0.6), Inches(0.5),
                prob["title"], font_size=18, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)
    
    # Body
    add_textbox(slide2, x + Inches(0.3), card_top + Inches(1.1), card_w - Inches(0.6), Inches(2.5),
                prob["body"], font_size=12, font_color=TEXT_SECONDARY)

# Bottom quote
add_textbox(slide2, Inches(1.0), Inches(6.5), Inches(11), Inches(0.5),
            "\"The problem isn't the model. The problem is the architecture.\"",
            font_size=14, font_color=PURPLE_LIGHT, alignment=PP_ALIGN.CENTER,
            font_name=FONT_HEADING)

add_slide_number(slide2, 2)


# ============================================================
# SLIDE 3 — THE COMPLETE AI APPLICATION STACK (Feedback #1)
# ============================================================

slide3 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide3, BG_DARK)
add_branding(slide3)

# Title
add_textbox(slide3, MARGIN_LEFT, Inches(0.7), Inches(8), Inches(0.7),
            "The Complete AI Application Stack",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide3, MARGIN_LEFT, Inches(1.3), Inches(8), Inches(0.4),
            "Six layers required for production AI systems.",
            font_size=14, font_color=TEXT_SECONDARY)

# Architecture layers — vertical stack on the left side
layers = [
    {"num": "01", "name": "User Experience Layer",       "desc": "Chat · Voice · Automation · UI Interfaces",                    "color": BLUE,    "accent": False},
    {"num": "02", "name": "Agent Orchestration Layer",    "desc": "Planning · Routing · Tool Use · Multi-Agent Coordination",    "color": BLUE,    "accent": False},
    {"num": "03", "name": "Business Knowledge Layer",     "desc": "Product Catalog · CRM · Documentation · Policies · Pricing", "color": GREEN,   "accent": False},
    {"num": "04", "name": "Context & Memory Layer",       "desc": "Preferences · Goals · Facts · User History · Behavior",       "color": PURPLE,  "accent": True},
    {"num": "05", "name": "Retrieval Layer",              "desc": "Semantic Search · Metadata Filters · Ranking · Assembly",     "color": CYAN,    "accent": False},
    {"num": "06", "name": "Infrastructure Layer",         "desc": "Vector Store · SQL · Object Storage · Compute · Monitoring",  "color": ORANGE,  "accent": False},
]

layer_x = Inches(0.8)
layer_w = Inches(7.5)
layer_h = Inches(0.7)
layer_gap = Inches(0.12)
start_y = Inches(2.0)

for i, layer in enumerate(layers):
    y = start_y + i * (layer_h + layer_gap)
    
    # Background bar
    bg_color = RGBColor(0x1F, 0x15, 0x3D) if layer["accent"] else BG_CARD
    border = PURPLE if layer["accent"] else CARD_BORDER
    add_rounded_rect(slide3, layer_x, y, layer_w, layer_h, bg_color, border, Pt(2) if layer["accent"] else Pt(1))
    
    # Number
    add_textbox(slide3, layer_x + Inches(0.2), y + Inches(0.08), Inches(0.5), Inches(0.3),
                layer["num"], font_size=11, font_color=layer["color"], bold=True, font_name=FONT_HEADING)
    
    # Layer name
    name_color = WHITE if layer["accent"] else TEXT_PRIMARY
    add_textbox(slide3, layer_x + Inches(0.6), y + Inches(0.05), Inches(3.5), Inches(0.35),
                layer["name"], font_size=16, font_color=name_color, bold=True, font_name=FONT_HEADING)
    
    # CORE badge for Context & Memory
    if layer["accent"]:
        add_textbox(slide3, layer_x + Inches(4.0), y + Inches(0.1), Inches(0.8), Inches(0.25),
                    "◆ CORE", font_size=10, font_color=PURPLE_LIGHT, bold=True, font_name=FONT_HEADING)
    
    # Description
    add_textbox(slide3, layer_x + Inches(0.6), y + Inches(0.38), Inches(6.5), Inches(0.3),
                layer["desc"], font_size=10, font_color=TEXT_SECONDARY)
    
    # Arrow between layers
    if i < len(layers) - 1:
        arrow_y = y + layer_h + Inches(0.01)
        add_textbox(slide3, layer_x + Inches(3.5), arrow_y, Inches(0.5), Inches(0.15),
                    "▼", font_size=8, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

# Right side — Key Insight callout
callout_x = Inches(8.8)
callout_w = Inches(4.0)

add_rounded_rect(slide3, callout_x, Inches(2.0), callout_w, Inches(2.2), 
                 RGBColor(0x0F, 0x1A, 0x0F), GREEN)

add_textbox(slide3, callout_x + Inches(0.3), Inches(2.15), callout_w - Inches(0.6), Inches(0.35),
            "Key Distinction", font_size=14, font_color=GREEN, bold=True, font_name=FONT_HEADING)

add_textbox(slide3, callout_x + Inches(0.3), Inches(2.6), callout_w - Inches(0.6), Inches(1.4),
            "Business Knowledge tells\nthe AI about the company.\n\nMemory tells the AI\nabout the user.",
            font_size=14, font_color=TEXT_PRIMARY, bold=True, alignment=PP_ALIGN.LEFT)

# Right side — What's new callout
add_rounded_rect(slide3, callout_x, Inches(4.5), callout_w, Inches(2.6), BG_CARD, CARD_BORDER)

add_textbox(slide3, callout_x + Inches(0.3), Inches(4.65), callout_w - Inches(0.6), Inches(0.3),
            "Why 6 Layers?", font_size=14, font_color=PURPLE_LIGHT, bold=True, font_name=FONT_HEADING)

why_text = (
    "Most AI architectures collapse Knowledge and Memory into a single layer. "
    "This creates systems that know about the company OR the user — but not both.\n\n"
    "Separating them enables:\n"
    "• Company knowledge shared across all users\n"
    "• User memory isolated per individual\n"
    "• Independent scaling of each layer"
)
add_textbox(slide3, callout_x + Inches(0.3), Inches(5.1), callout_w - Inches(0.6), Inches(2.0),
            why_text, font_size=11, font_color=TEXT_SECONDARY)

add_slide_number(slide3, 3)


# ============================================================
# SLIDE 4 — KNOWLEDGE vs MEMORY (NEW — Feedback #4)
# ============================================================

slide4 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide4, BG_DARK)
add_branding(slide4)

# Title
add_textbox(slide4, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Knowledge vs Memory",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide4, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "Two distinct data planes that serve fundamentally different purposes.",
            font_size=14, font_color=TEXT_SECONDARY)

# LEFT COLUMN — Knowledge
col_w = Inches(5.2)
col_h = Inches(3.8)
left_x = Inches(0.8)
right_x = Inches(6.8)
col_top = Inches(2.0)

# Knowledge card
add_rounded_rect(slide4, left_x, col_top, col_w, col_h, RGBColor(0x0F, 0x1A, 0x0F), GREEN)

add_textbox(slide4, left_x + Inches(0.3), col_top + Inches(0.2), col_w - Inches(0.6), Inches(0.4),
            "Business Knowledge", font_size=22, font_color=GREEN, bold=True, font_name=FONT_HEADING)

add_textbox(slide4, left_x + Inches(0.3), col_top + Inches(0.65), col_w - Inches(0.6), Inches(0.3),
            "What the company knows", font_size=14, font_color=TEXT_SECONDARY)

knowledge_items = [
    "📋  Product Catalog & Pricing",
    "📄  Documentation & Guides",
    "🏢  CRM & Customer Records",
    "📜  Policies & Compliance Rules",
    "💬  Internal Knowledge Base",
]

for j, item in enumerate(knowledge_items):
    add_textbox(slide4, left_x + Inches(0.4), col_top + Inches(1.2) + j * Inches(0.45),
                col_w - Inches(0.8), Inches(0.4),
                item, font_size=14, font_color=TEXT_PRIMARY)

# Add characteristic
add_textbox(slide4, left_x + Inches(0.3), col_top + Inches(3.4), col_w - Inches(0.6), Inches(0.3),
            "Shared across all users", font_size=11, font_color=GREEN, bold=True)

# Memory card
add_rounded_rect(slide4, right_x, col_top, col_w, col_h, RGBColor(0x1A, 0x0F, 0x2E), PURPLE)

add_textbox(slide4, right_x + Inches(0.3), col_top + Inches(0.2), col_w - Inches(0.6), Inches(0.4),
            "User Memory", font_size=22, font_color=PURPLE_LIGHT, bold=True, font_name=FONT_HEADING)

add_textbox(slide4, right_x + Inches(0.3), col_top + Inches(0.65), col_w - Inches(0.6), Inches(0.3),
            "What the AI knows about the user", font_size=14, font_color=TEXT_SECONDARY)

memory_items = [
    "⚙️  User Preferences & Settings",
    "🎯  Goals & Objectives",
    "📊  Interaction History",
    "🔗  Relationships & Context",
    "📈  Behavioral Signals",
]

for j, item in enumerate(memory_items):
    add_textbox(slide4, right_x + Inches(0.4), col_top + Inches(1.2) + j * Inches(0.45),
                col_w - Inches(0.8), Inches(0.4),
                item, font_size=14, font_color=TEXT_PRIMARY)

add_textbox(slide4, right_x + Inches(0.3), col_top + Inches(3.4), col_w - Inches(0.6), Inches(0.3),
            "Isolated per user", font_size=11, font_color=PURPLE_LIGHT, bold=True)

# Bottom flow: Knowledge + Memory → Personalized AI
flow_y = Inches(6.1)

add_rounded_rect(slide4, Inches(1.5), flow_y, Inches(3.2), Inches(0.6), BG_CARD, GREEN)
add_textbox(slide4, Inches(1.5), flow_y + Inches(0.12), Inches(3.2), Inches(0.4),
            "Knowledge", font_size=16, font_color=GREEN, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_textbox(slide4, Inches(4.8), flow_y + Inches(0.1), Inches(0.6), Inches(0.4),
            "+", font_size=20, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

add_rounded_rect(slide4, Inches(5.4), flow_y, Inches(3.2), Inches(0.6), BG_CARD, PURPLE)
add_textbox(slide4, Inches(5.4), flow_y + Inches(0.12), Inches(3.2), Inches(0.4),
            "Memory", font_size=16, font_color=PURPLE_LIGHT, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_textbox(slide4, Inches(8.7), flow_y + Inches(0.1), Inches(0.8), Inches(0.4),
            "→", font_size=20, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

add_rounded_rect(slide4, Inches(9.5), flow_y, Inches(3.2), Inches(0.6), 
                 RGBColor(0x1A, 0x1A, 0x2E), RGBColor(0xF5, 0x9E, 0x0B))
add_textbox(slide4, Inches(9.5), flow_y + Inches(0.12), Inches(3.2), Inches(0.4),
            "Personalized AI", font_size=16, font_color=ORANGE, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide4, 4)


# ============================================================
# SLIDE 5 — HOW CONTEXT BECOMES MEMORY
# ============================================================

slide5 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide5, BG_DARK)
add_branding(slide5)

# Title
add_textbox(slide5, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "How Context Becomes Memory",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide5, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "A six-step pipeline that transforms raw interactions into structured, retrievable memory.",
            font_size=14, font_color=TEXT_SECONDARY)

# 6-step cards in 2 rows x 3 cols
steps = [
    {"num": "01", "title": "User Interaction",    "body": "Raw input captured from chat, voice, or automation. Signals include queries, preferences, and behavioral patterns."},
    {"num": "02", "title": "Context Extraction",   "body": "NLP pipeline identifies facts, goals, preferences, and decisions from raw interaction data."},
    {"num": "03", "title": "Structured Memory",    "body": "Extracted signals normalized into typed memory objects: Preferences · Goals · Decisions · Behavioral Signals"},
    {"num": "04", "title": "Persistent Storage",   "body": "Memory objects written to durable context store. Indexed for fast retrieval across all future sessions."},
    {"num": "05", "title": "Retrieval",            "body": "Relevant memory fetched via semantic search and metadata filters. Context assembled for LLM prompt injection."},
    {"num": "06", "title": "Personalized Response", "body": "LLM generates response grounded in user memory.\n\"Store meaning, not conversations.\""},
]

step_w = Inches(3.6)
step_h = Inches(2.1)
step_gap_x = Inches(0.35)
step_gap_y = Inches(0.3)
step_start_x = Inches(1.0)
step_start_y = Inches(2.0)

for i, step in enumerate(steps):
    row = i // 3
    col = i % 3
    x = step_start_x + col * (step_w + step_gap_x)
    y = step_start_y + row * (step_h + step_gap_y + Inches(0.3))
    
    # Card
    add_rounded_rect(slide5, x, y, step_w, step_h, BG_CARD, CARD_BORDER)
    
    # Step number
    add_textbox(slide5, x + Inches(0.2), y + Inches(0.15), Inches(0.5), Inches(0.3),
                step["num"], font_size=12, font_color=PURPLE_LIGHT, bold=True, font_name=FONT_HEADING)
    
    # Purple accent dot
    add_rect(slide5, x + Inches(0.2), y + Inches(0.12), Inches(0.04), Inches(0.3), PURPLE)
    
    # Title
    add_textbox(slide5, x + Inches(0.55), y + Inches(0.15), step_w - Inches(0.8), Inches(0.35),
                step["title"], font_size=15, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)
    
    # Body
    add_textbox(slide5, x + Inches(0.3), y + Inches(0.6), step_w - Inches(0.6), Inches(1.4),
                step["body"], font_size=11, font_color=TEXT_SECONDARY)
    
    # Arrow between columns
    if col < 2:
        arrow_x = x + step_w + Inches(0.08)
        add_textbox(slide5, arrow_x, y + Inches(0.85), Inches(0.2), Inches(0.3),
                    "→", font_size=14, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

# Arrow between rows
for col in range(3):
    ax = step_start_x + col * (step_w + step_gap_x) + step_w / 2 - Inches(0.1)
    ay = step_start_y + step_h + Inches(0.05)
    if col == 2:
        # Only show arrow going down from last column
        add_textbox(slide5, ax, ay, Inches(0.3), Inches(0.3),
                    "▼", font_size=10, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

add_slide_number(slide5, 5)


# ============================================================
# SLIDE 6 — CONTEXT ISOLATION (NEW — Feedback #2)
# ============================================================

slide6 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide6, BG_DARK)
add_branding(slide6)

# Title
add_textbox(slide6, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Context Isolation",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide6, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "Every user accumulates a unique context profile over time — fully isolated.",
            font_size=14, font_color=TEXT_SECONDARY)

# Three user columns
users = [
    {"name": "User A", "icon": "👤", "memories": ["Preference: Vegetarian", "Goal: Weight loss", "History: 47 sessions", "Tone: Casual"]},
    {"name": "User B", "icon": "👤", "memories": ["Preference: Keto diet", "Goal: Muscle gain", "History: 12 sessions", "Tone: Professional"]},
    {"name": "User C", "icon": "👤", "memories": ["Preference: Vegan", "Goal: Recipe discovery", "History: 203 sessions", "Tone: Friendly"]},
]

user_w = Inches(3.2)
user_gap = Inches(0.6)
user_start_x = Inches(1.5)
user_top = Inches(2.2)

for i, user in enumerate(users):
    x = user_start_x + i * (user_w + user_gap)
    
    # User box
    add_rounded_rect(slide6, x, user_top, user_w, Inches(0.6), BG_CARD, BLUE)
    add_textbox(slide6, x, user_top + Inches(0.12), user_w, Inches(0.4),
                f"{user['icon']}  {user['name']}", font_size=16, font_color=TEXT_PRIMARY, 
                bold=True, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)
    
    # Arrow down
    add_textbox(slide6, x + user_w/2 - Inches(0.15), user_top + Inches(0.65), Inches(0.3), Inches(0.3),
                "▼", font_size=10, font_color=PURPLE_LIGHT, alignment=PP_ALIGN.CENTER)
    
    # Memory box
    mem_top = user_top + Inches(1.0)
    add_rounded_rect(slide6, x, mem_top, user_w, Inches(2.2), RGBColor(0x1A, 0x0F, 0x2E), PURPLE)
    
    add_textbox(slide6, x + Inches(0.2), mem_top + Inches(0.1), user_w - Inches(0.4), Inches(0.35),
                f"Memory {chr(65+i)}", font_size=14, font_color=PURPLE_LIGHT, bold=True, font_name=FONT_HEADING)
    
    for j, mem in enumerate(user["memories"]):
        add_textbox(slide6, x + Inches(0.3), mem_top + Inches(0.5) + j * Inches(0.38),
                    user_w - Inches(0.6), Inches(0.35),
                    f"•  {mem}", font_size=11, font_color=TEXT_SECONDARY)

# Arrows converging down to AI Layer
ai_layer_top = Inches(5.6)

# Convergence arrows
for i in range(3):
    x = user_start_x + i * (user_w + user_gap) + user_w/2 - Inches(0.15)
    add_textbox(slide6, x, ai_layer_top - Inches(0.35), Inches(0.3), Inches(0.3),
                "▼", font_size=10, font_color=ORANGE, alignment=PP_ALIGN.CENTER)

# Shared AI Layer bar
add_rounded_rect(slide6, Inches(1.0), ai_layer_top, Inches(11.3), Inches(0.7), BG_CARD, ORANGE)
add_textbox(slide6, Inches(1.0), ai_layer_top + Inches(0.15), Inches(11.3), Inches(0.4),
            "🤖  Shared AI Layer  —  Same model, same APIs, personalized for each user",
            font_size=15, font_color=ORANGE, bold=True, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Bottom stat callout
add_rounded_rect(slide6, Inches(2.5), Inches(6.6), Inches(8.3), Inches(0.6), BG_CARD, CARD_BORDER)
add_textbox(slide6, Inches(2.5), Inches(6.7), Inches(8.3), Inches(0.4),
            "100,000 Users  →  100,000 Unique Context Profiles  →  Zero Shared State",
            font_size=15, font_color=TEXT_PRIMARY, bold=True, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide6, 6)


# ============================================================
# SLIDE 7 — ENTERPRISE ARCHITECTURE (NEW — Feedback #5)
# ============================================================

slide7 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide7, BG_DARK)
add_branding(slide7)

# Title
add_textbox(slide7, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Enterprise Architecture",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide7, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "How Persistent Context Infrastructure integrates into production AI systems.",
            font_size=14, font_color=TEXT_SECONDARY)

# Main vertical stack — left side
stack_layers = [
    {"name": "Web App / Mobile / Automation",   "color": BLUE,    "desc": "Client-facing interfaces"},
    {"name": "Agent Gateway",                    "color": BLUE,    "desc": "Routing · Auth · Rate Limiting"},
    {"name": "Context Layer",                    "color": PURPLE,  "desc": "Memory Engine · Context Assembly"},
    {"name": "Knowledge Layer",                  "color": GREEN,   "desc": "Business Knowledge Retrieval"},
    {"name": "LLM Layer",                        "color": ORANGE,  "desc": "Model Inference · Response Generation"},
    {"name": "Storage Layer",                    "color": TEXT_MUTED, "desc": "Vector Store · SQL · Object Storage"},
]

stack_x = Inches(0.8)
stack_w = Inches(6.5)
stack_h = Inches(0.65)
stack_gap = Inches(0.1)
stack_top = Inches(2.0)

for i, layer in enumerate(stack_layers):
    y = stack_top + i * (stack_h + stack_gap + Inches(0.15))
    
    is_context = (layer["name"] == "Context Layer")
    bg = RGBColor(0x1F, 0x15, 0x3D) if is_context else BG_CARD
    border = layer["color"]
    
    add_rounded_rect(slide7, stack_x, y, stack_w, stack_h, bg, border, Pt(2) if is_context else Pt(1))
    
    add_textbox(slide7, stack_x + Inches(0.3), y + Inches(0.08), Inches(4.5), Inches(0.35),
                layer["name"], font_size=15, font_color=TEXT_PRIMARY if not is_context else WHITE, 
                bold=True, font_name=FONT_HEADING)
    
    add_textbox(slide7, stack_x + Inches(0.3), y + Inches(0.38), Inches(5.8), Inches(0.25),
                layer["desc"], font_size=10, font_color=TEXT_SECONDARY)
    
    # Arrow
    if i < len(stack_layers) - 1:
        add_textbox(slide7, stack_x + stack_w/2 - Inches(0.15), y + stack_h, Inches(0.3), Inches(0.2),
                    "▼", font_size=8, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

# Right side — Data Sources feeding Knowledge Layer
sources_x = Inches(8.2)
sources_w = Inches(4.5)
sources_top = Inches(2.0)

add_textbox(slide7, sources_x, sources_top, sources_w, Inches(0.4),
            "Data Sources", font_size=16, font_color=GREEN, bold=True, font_name=FONT_HEADING)

data_sources = [
    {"name": "CRM",            "desc": "Customer records & profiles", "icon": "🏢"},
    {"name": "Documentation",  "desc": "Product docs & guides",      "icon": "📄"},
    {"name": "Database",       "desc": "Structured business data",   "icon": "🗄️"},
    {"name": "Slack / Email",  "desc": "Communication history",      "icon": "💬"},
    {"name": "APIs",           "desc": "Third-party integrations",   "icon": "🔌"},
]

for j, src in enumerate(data_sources):
    sy = sources_top + Inches(0.5) + j * Inches(0.75)
    
    add_rounded_rect(slide7, sources_x, sy, sources_w, Inches(0.6), BG_CARD, CARD_BORDER)
    
    add_textbox(slide7, sources_x + Inches(0.15), sy + Inches(0.08), sources_w - Inches(0.3), Inches(0.3),
                f"{src['icon']}  {src['name']}", font_size=13, font_color=TEXT_PRIMARY, bold=True)
    
    add_textbox(slide7, sources_x + Inches(0.55), sy + Inches(0.32), sources_w - Inches(0.7), Inches(0.25),
                src["desc"], font_size=10, font_color=TEXT_SECONDARY)

# Arrow from data sources to knowledge layer
# The knowledge layer is at index 3, so calculate its y position
knowledge_y = stack_top + 3 * (stack_h + stack_gap + Inches(0.15))
add_textbox(slide7, Inches(7.5), knowledge_y + Inches(0.15), Inches(0.6), Inches(0.4),
            "←", font_size=18, font_color=GREEN, alignment=PP_ALIGN.CENTER)

# Bottom note
add_textbox(slide7, Inches(1.0), Inches(6.9), Inches(11.3), Inches(0.4),
            "Context Layer is infrastructure — not a feature. It sits between your application and your models.",
            font_size=13, font_color=PURPLE_LIGHT, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide7, 7)


# ============================================================
# SLIDE 8 — TYPICAL INTEGRATION (Reworked — Feedback #3)
# ============================================================

slide8 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide8, BG_DARK)
add_branding(slide8)

# Title
add_textbox(slide8, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Typical Integration",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide8, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "When to call each API — mapped to your application lifecycle.",
            font_size=14, font_color=TEXT_SECONDARY)

# Three integration flows
flows = [
    {
        "trigger": "User Signup",
        "arrow": "→",
        "endpoint": "POST /process_raw",
        "desc": "Convert onboarding data into structured memory.\nCRM import · Chat history · Initial preferences",
        "color": GREEN,
        "example": '{ "user_id": "u_123",\n  "conversation": "..." }',
    },
    {
        "trigger": "User Chats",
        "arrow": "→",
        "endpoint": "POST /agent_chat",
        "desc": "Generate responses using stored context.\nMemory retrieval + LLM response — fully automatic.",
        "color": PURPLE,
        "example": '{ "user_id": "u_123",\n  "query": "Recommend restaurants" }',
        "primary": True,
    },
    {
        "trigger": "Profile Page",
        "arrow": "→",
        "endpoint": "POST /get_context",
        "desc": "Retrieve stored user memory directly.\nProfile display · Agent context · Auditing",
        "color": CYAN,
        "example": '{ "user_id": "u_123",\n  "query": "user preferences" }',
    },
]

flow_top = Inches(2.1)
flow_h = Inches(1.5)
flow_gap = Inches(0.3)

for i, flow in enumerate(flows):
    y = flow_top + i * (flow_h + flow_gap)
    
    # Full row background
    is_primary = flow.get("primary", False)
    row_bg = RGBColor(0x1A, 0x0F, 0x2E) if is_primary else BG_CARD
    row_border = flow["color"] if is_primary else CARD_BORDER
    add_rounded_rect(slide8, Inches(0.8), y, Inches(11.7), flow_h, row_bg, row_border, 
                     Pt(2) if is_primary else Pt(1))
    
    # Primary badge
    if is_primary:
        add_textbox(slide8, Inches(11.0), y + Inches(0.1), Inches(1.3), Inches(0.25),
                    "◆ PRIMARY", font_size=9, font_color=PURPLE_LIGHT, bold=True,
                    alignment=PP_ALIGN.RIGHT, font_name=FONT_HEADING)
    
    # Trigger
    add_textbox(slide8, Inches(1.1), y + Inches(0.2), Inches(1.8), Inches(0.35),
                flow["trigger"], font_size=17, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)
    
    # Arrow
    add_textbox(slide8, Inches(2.9), y + Inches(0.2), Inches(0.5), Inches(0.35),
                "→", font_size=18, font_color=flow["color"], alignment=PP_ALIGN.CENTER)
    
    # Endpoint (code-style)
    add_rounded_rect(slide8, Inches(3.4), y + Inches(0.15), Inches(2.5), Inches(0.4), 
                     RGBColor(0x0D, 0x0D, 0x14), flow["color"])
    add_textbox(slide8, Inches(3.5), y + Inches(0.2), Inches(2.3), Inches(0.35),
                flow["endpoint"], font_size=13, font_color=flow["color"], bold=True,
                font_name="Consolas")
    
    # Description
    add_textbox(slide8, Inches(3.4), y + Inches(0.65), Inches(3.5), Inches(0.8),
                flow["desc"], font_size=11, font_color=TEXT_SECONDARY)
    
    # Code example
    add_rounded_rect(slide8, Inches(7.5), y + Inches(0.15), Inches(4.7), Inches(1.2),
                     RGBColor(0x0A, 0x0A, 0x12), RGBColor(0x2D, 0x2D, 0x4A))
    add_textbox(slide8, Inches(7.7), y + Inches(0.25), Inches(4.3), Inches(1.0),
                flow["example"], font_size=11, font_color=TEXT_SECONDARY,
                font_name="Consolas")

# Bottom principle
add_textbox(slide8, Inches(1.0), Inches(6.8), Inches(11.3), Inches(0.4),
            "All APIs operate on structured memory objects — not raw conversation text.",
            font_size=13, font_color=PURPLE_LIGHT, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide8, 8)


# ============================================================
# SLIDE 9 — END-TO-END REQUEST FLOW
# ============================================================

slide9 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide9, BG_DARK)
add_branding(slide9)

# Title
add_textbox(slide9, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "End-to-End Request Flow",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

add_textbox(slide9, MARGIN_LEFT, Inches(1.3), Inches(10), Inches(0.4),
            "What happens when a user sends a message — from input to personalized response.",
            font_size=14, font_color=TEXT_SECONDARY)

# 6-step flow (2 rows x 3 cols)
flow_steps = [
    {"num": "01", "title": "User",                    "body": "User sends a query or message. Entry point of every interaction. Session context initialized."},
    {"num": "02", "title": "Agent API",                "body": "Request received. Authentication validated. Memory retrieval and business knowledge fetch triggered automatically."},
    {"num": "03", "title": "Retrieve Memory + Knowledge", "body": "Memory Engine fetches stored user context. Business Knowledge queried in parallel. Preferences, goals, and facts assembled."},
    {"num": "04", "title": "Context Assembly",         "body": "Retrieved memory merged with business knowledge. Structured context payload built for LLM. Token-optimized and ranked by relevance."},
    {"num": "05", "title": "LLM → Response",           "body": "Assembled context injected into LLM prompt. Personalized response generated with full contextual awareness."},
    {"num": "06", "title": "Async Memory Update",      "body": "Memory updated asynchronously post-response. New facts, preferences, and signals extracted. No latency added to user response."},
]

for i, step in enumerate(flow_steps):
    row = i // 3
    col = i % 3
    x = step_start_x + col * (step_w + step_gap_x)
    y = Inches(2.0) + row * (step_h + Inches(0.6))
    
    add_rounded_rect(slide9, x, y, step_w, step_h, BG_CARD, CARD_BORDER)
    
    # Step number
    step_color = PURPLE_LIGHT
    add_textbox(slide9, x + Inches(0.2), y + Inches(0.15), Inches(0.5), Inches(0.3),
                step["num"], font_size=12, font_color=step_color, bold=True, font_name=FONT_HEADING)
    
    add_rect(slide9, x + Inches(0.2), y + Inches(0.12), Inches(0.04), Inches(0.3), PURPLE)
    
    add_textbox(slide9, x + Inches(0.55), y + Inches(0.15), step_w - Inches(0.8), Inches(0.35),
                step["title"], font_size=15, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)
    
    add_textbox(slide9, x + Inches(0.3), y + Inches(0.6), step_w - Inches(0.6), Inches(1.4),
                step["body"], font_size=11, font_color=TEXT_SECONDARY)
    
    # Arrows between columns
    if col < 2:
        arrow_x = x + step_w + Inches(0.08)
        add_textbox(slide9, arrow_x, y + Inches(0.85), Inches(0.2), Inches(0.3),
                    "→", font_size=14, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

# Arrow from row 1 to row 2
ax = step_start_x + 2 * (step_w + step_gap_x) + step_w / 2 - Inches(0.1)
ay = Inches(2.0) + step_h + Inches(0.08)
add_textbox(slide9, ax, ay, Inches(0.3), Inches(0.3),
            "▼", font_size=10, font_color=TEXT_MUTED, alignment=PP_ALIGN.CENTER)

add_slide_number(slide9, 9)


# ============================================================
# SLIDE 10 — SYSTEM COMPONENTS
# ============================================================

slide10 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide10, BG_DARK)
add_branding(slide10)

# Title
add_textbox(slide10, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "System Components",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

# Component groups
components = [
    {
        "title": "Frontend  →  API Layer  →  Memory Engine",
        "color": BLUE,
        "items": [
            "Frontend: Receives user input (chat, voice, automation).",
            "API Layer: Routes requests, authenticates, orchestrates calls.",
            "Memory Engine: Extracts, stores, and retrieves structured context.",
        ]
    },
    {
        "title": "Context Store  →  Knowledge Sources",
        "color": GREEN,
        "items": [
            "Context Store: Persistent vector + metadata storage for user context.",
            "Knowledge Sources: CRM, docs, product data — business-level knowledge.",
        ]
    },
    {
        "title": "LLM  →  Async Memory Update",
        "color": PURPLE,
        "items": [
            "LLM: Receives assembled context + user query, generates response.",
            "Async Update: Post-response pipeline extracts new facts automatically.",
        ]
    },
]

comp_top = Inches(1.6)
comp_h = Inches(1.65)
comp_gap = Inches(0.25)

for i, comp in enumerate(components):
    y = comp_top + i * (comp_h + comp_gap)
    
    add_rounded_rect(slide10, Inches(0.8), y, Inches(11.7), comp_h, BG_CARD, CARD_BORDER)
    
    # Color accent bar
    add_rect(slide10, Inches(0.8), y, Inches(0.06), comp_h, comp["color"])
    
    # Title
    add_textbox(slide10, Inches(1.2), y + Inches(0.15), Inches(10.5), Inches(0.4),
                comp["title"], font_size=17, font_color=comp["color"], bold=True, font_name=FONT_HEADING)
    
    # Items
    for j, item in enumerate(comp["items"]):
        add_textbox(slide10, Inches(1.4), y + Inches(0.6) + j * Inches(0.32), Inches(10.5), Inches(0.3),
                    f"•  {item}", font_size=12, font_color=TEXT_SECONDARY)

add_slide_number(slide10, 10)


# ============================================================
# SLIDE 11 — BUSINESS IMPACT
# ============================================================

slide11 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide11, BG_DARK)
add_branding(slide11)

# Title
add_textbox(slide11, MARGIN_LEFT, Inches(0.7), Inches(10), Inches(0.7),
            "Business Impact",
            font_size=32, font_color=TEXT_PRIMARY, bold=True, font_name=FONT_HEADING)

# Impact cards — 3x2 grid
impacts = [
    {"title": "Personalized Onboarding",     "body": "AI systems learn user preferences from first interaction — no repeated setup, no lost context.", "icon": "✦"},
    {"title": "Persistent User Understanding", "body": "Continuous memory accumulation builds a deep model of each user — retained indefinitely.", "icon": "✦"},
    {"title": "Reduced Token Costs",           "body": "Stored memory replaces repetitive context injection — shorter prompts, lower costs, faster inference.", "icon": "✦"},
    {"title": "Better AI Accuracy",            "body": "Responses grounded in real user history outperform generic LLM outputs — improves with every interaction.", "icon": "✦"},
    {"title": "Cross-Session Continuity",      "body": "Every session builds on the last — users never re-explain themselves across interactions.", "icon": "✦"},
    {"title": "Long-Term Customer Intelligence", "body": "AI accumulates behavioral signals that surface insights no single session could provide.", "icon": "✦"},
]

impact_w = Inches(5.6)
impact_h = Inches(1.35)
impact_gap_x = Inches(0.4)
impact_gap_y = Inches(0.3)
impact_start_x = Inches(0.8)
impact_start_y = Inches(1.7)

for i, imp in enumerate(impacts):
    row = i // 2
    col = i % 2
    x = impact_start_x + col * (impact_w + impact_gap_x)
    y = impact_start_y + row * (impact_h + impact_gap_y)
    
    add_rounded_rect(slide11, x, y, impact_w, impact_h, BG_CARD, CARD_BORDER)
    
    # Purple accent
    add_rect(slide11, x, y, Inches(0.05), impact_h, PURPLE)
    
    # Title
    add_textbox(slide11, x + Inches(0.3), y + Inches(0.15), impact_w - Inches(0.6), Inches(0.35),
                f"{imp['icon']}  {imp['title']}", font_size=15, font_color=TEXT_PRIMARY, 
                bold=True, font_name=FONT_HEADING)
    
    # Body
    add_textbox(slide11, x + Inches(0.3), y + Inches(0.55), impact_w - Inches(0.6), Inches(0.7),
                imp["body"], font_size=12, font_color=TEXT_SECONDARY)

# Bottom quote
add_textbox(slide11, Inches(1.0), Inches(6.7), Inches(11.3), Inches(0.5),
            "\"The future of AI is not larger context windows.\nThe future is Memory + Business Knowledge + Retrieval + Reasoning.\"",
            font_size=14, font_color=PURPLE_LIGHT, alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide11, 11)


# ============================================================
# SLIDE 12 — FOUR PILLARS CLOSING (NEW — Feedback #7)
# ============================================================

slide12 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide12, BG_DARK)

# Top accent bar
add_rect(slide12, Inches(0), Inches(0), SLIDE_W, Inches(0.04), PURPLE)

# Main statement
add_textbox(slide12, Inches(1.5), Inches(1.5), Inches(10.3), Inches(0.8),
            "Modern AI Systems Require Four Layers",
            font_size=34, font_color=TEXT_PRIMARY, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Four pillars as horizontal blocks
pillars = [
    {"name": "Knowledge",  "color": GREEN,  "desc": "What the company knows"},
    {"name": "Memory",     "color": PURPLE,  "desc": "What the AI knows about the user"},
    {"name": "Retrieval",  "color": CYAN,    "desc": "Finding the right context at the right time"},
    {"name": "Reasoning",  "color": ORANGE,  "desc": "Generating grounded, personalized responses"},
]

pillar_w = Inches(2.6)
pillar_h = Inches(1.8)
pillar_gap = Inches(0.3)
pillar_start_x = Inches(0.9)
pillar_top = Inches(2.7)

for i, pillar in enumerate(pillars):
    x = pillar_start_x + i * (pillar_w + pillar_gap)
    
    # Pillar card
    add_rounded_rect(slide12, x, pillar_top, pillar_w, pillar_h, BG_CARD, pillar["color"], Pt(2))
    
    # Colored top accent
    add_rect(slide12, x + Inches(0.3), pillar_top + Inches(0.25), Inches(0.6), Inches(0.04), pillar["color"])
    
    # Name
    add_textbox(slide12, x, pillar_top + Inches(0.5), pillar_w, Inches(0.5),
                pillar["name"], font_size=22, font_color=pillar["color"], bold=True,
                alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)
    
    # Description
    add_textbox(slide12, x + Inches(0.2), pillar_top + Inches(1.1), pillar_w - Inches(0.4), Inches(0.6),
                pillar["desc"], font_size=12, font_color=TEXT_SECONDARY,
                alignment=PP_ALIGN.CENTER)

# Warning statement
add_textbox(slide12, Inches(1.5), Inches(4.9), Inches(10.3), Inches(0.5),
            "Remove any one layer and personalization breaks.",
            font_size=18, font_color=RED_SOFT, bold=True,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Divider
add_rect(slide12, Inches(5.4), Inches(5.5), Inches(2.5), Inches(0.03), PURPLE)

# Closing statement
add_textbox(slide12, Inches(1.5), Inches(5.8), Inches(10.3), Inches(1.2),
            "Persistent Context Infrastructure\nbecomes the foundation that allows AI\nto understand users over time.",
            font_size=22, font_color=TEXT_PRIMARY, bold=False,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

# Branding
add_textbox(slide12, Inches(5.0), Inches(7.0), Inches(3.3), Inches(0.3),
            "Aldenaire International", font_size=11, font_color=PURPLE_LIGHT,
            alignment=PP_ALIGN.CENTER, font_name=FONT_HEADING)

add_slide_number(slide12, 12)


# ============================================================
# SLIDE 5B — USER LIFECYCLE (integrated after Context Becomes Memory)
# Let's keep this as the original had it — but let me not add it 
# since we covered the content in other slides.
# ============================================================


# ============================================================
# SAVE
# ============================================================

output_path = r"C:\Users\Dellg\Downloads\Persistent Context Infrastructure v4.pptx"
prs.save(output_path)
print(f"\n[OK] Presentation saved to: {output_path}")
print(f"   Total slides: {len(prs.slides)}")

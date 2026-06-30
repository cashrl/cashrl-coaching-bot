"""
RLBotPro - Evolution Charts
Gráficos de evolução de performance ao longo do tempo.
"""
import flet as ft
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

# Cores do gráfico
CHART_COLORS = {
    'primary': '#2563eb',
    'secondary': '#7c3aed',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'cyan': '#06b6d4',
    'pink': '#ec4899',
    'surface': '#1a1d27',
    'text': '#e4e4e7',
    'text_secondary': '#a1a1aa',
    'border': '#27272a',
}


def create_evolution_chart(
    data: List[Dict[str, Any]],
    stat_key: str,
    title: str,
    color: str = CHART_COLORS['primary'],
    unit: str = ""
) -> ft.Container:
    """
    Cria um gráfico de evolução para uma stat específica.
    
    Args:
        data: Lista de dados (cada item é um match com timestamp)
        stat_key: Chave da stat para mostrar
        title: Título do gráfico
        color: Cor da linha
        unit: Unidade de medida
    """
    if not data:
        return _empty_chart(title)
    
    # Extrair valores
    values = []
    labels = []
    
    for i, item in enumerate(data):
        value = item.get(stat_key, 0)
        values.append(value)
        # Label: data ou índice
        if "timestamp" in item:
            try:
                dt = datetime.fromisoformat(item["timestamp"])
                labels.append(dt.strftime("%d/%m"))
            except:
                labels.append(str(i + 1))
        else:
            labels.append(str(i + 1))
    
    # Criar pontos para o gráfico
    chart_data = []
    for i, (val, label) in enumerate(zip(values, labels)):
        chart_data.append(
            ft.LineChartDataPoint(
                x=float(i),
                y=float(val) if val else 0
            )
        )
    
    # Criar gráfico de linha
    line_chart = ft.LineChartData(
        data_points=chart_data,
        color=color,
        stroke_width=3,
        curved=True,
        below_line_gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=[color + "40", color + "00"]
        )
    )
    
    chart = ft.LineChart(
        data=[line_chart],
        expand=True,
        min_y=0,
        max_y=max(values) * 1.2 if values else 100,
        min_x=0,
        max_x=max(len(values) - 1, 1),
        left_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=str(int(i * max(values) / 4)) if values else "0",
                    style=ft.TextStyle(size=10, color=CHART_COLORS['text_secondary'])
                )
                for i in range(5)
            ],
            labels_size=40
        ),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=labels[i] if i < len(labels) else "",
                    style=ft.TextStyle(size=10, color=CHART_COLORS['text_secondary'])
                )
                for i in range(0, len(labels), max(1, len(labels) // 5))
            ],
            labels_size=40
        ),
        tooltip_bgcolor=CHART_COLORS['surface'],
        tooltip=get_tooltip_color(color),
    )
    
    # Calcular variação
    if len(values) >= 2:
        first_val = values[0]
        last_val = values[-1]
        if first_val > 0:
            variation = ((last_val - first_val) / first_val) * 100
        else:
            variation = 0
        variation_color = CHART_COLORS['success'] if variation >= 0 else CHART_COLORS['error']
        variation_text = f"+{variation:.1f}%" if variation >= 0 else f"{variation:.1f}%"
    else:
        variation_color = CHART_COLORS['text_secondary']
        variation_text = "N/A"
    
    # Valor atual
    current_value = values[-1] if values else 0
    
    return ft.Container(
        content=ft.Column(
            controls=[
                # Header com título e variação
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(title, size=12, weight=ft.FontWeight.W_600, 
                                        color=CHART_COLORS['text_secondary']),
                                ft.Text(f"{current_value:.1f}{unit}", size=24, 
                                        weight=ft.FontWeight.BOLD, color=color),
                            ],
                            spacing=2
                        ),
                        ft.Container(
                            content=ft.Text(variation_text, size=12, weight=ft.FontWeight.W_600,
                                          color=variation_color),
                            bgcolor=variation_color + "20",
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START
                ),
                ft.Container(height=8),
                # Gráfico
                ft.Container(
                    content=chart,
                    height=150,
                    bgcolor=CHART_COLORS['surface'],
                    border_radius=10,
                    border=ft.border.all(1, CHART_COLORS['border'])
                ),
            ],
            spacing=0
        ),
        expand=True
    )


def _empty_chart(title: str) -> ft.Container:
    """Retorna um gráfico vazio."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=12, weight=ft.FontWeight.W_600, 
                        color=CHART_COLORS['text_secondary']),
                ft.Container(height=20),
                ft.Icon(ft.Icons.SHOW_CHART_ROUNDED, size=32, 
                       color=CHART_COLORS['text_secondary']),
                ft.Text("Sem dados suficientes", size=11, 
                       color=CHART_COLORS['text_secondary']),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4
        ),
        height=200,
        bgcolor=CHART_COLORS['surface'],
        border_radius=10,
        border=ft.border.all(1, CHART_COLORS['border']),
        expand=True
    )


def get_tooltip_color(color: str) -> str:
    """Retorna cor para o tooltip."""
    return color + "E0"


def create_stats_grid(match_history: List[Dict]) -> ft.Container:
    """
    Cria um grid de stats comparativo (atual vs anterior).
    """
    if not match_history or len(match_history) < 2:
        return ft.Container(
            content=ft.Text("Histórico insuficiente para comparação", 
                          size=12, color=CHART_COLORS['text_secondary']),
            height=100
        )
    
    current = match_history[-1]
    previous = match_history[-2]
    
    stats = [
        ("Gols", "goals", CHART_COLORS['primary']),
        ("Assists", "assists", CHART_COLORS['cyan']),
        ("Saves", "saves", CHART_COLORS['success']),
        ("Shots", "shots", CHART_COLORS['warning']),
        ("Score", "score", CHART_COLORS['secondary']),
    ]
    
    controls = []
    for title, key, color in stats:
        curr_val = current.get(key, 0)
        prev_val = previous.get(key, 0)
        
        if prev_val > 0:
            change = curr_val - prev_val
            change_color = CHART_COLORS['success'] if change >= 0 else CHART_COLORS['error']
            change_text = f"+{change}" if change >= 0 else str(change)
        else:
            change_color = CHART_COLORS['text_secondary']
            change_text = "-"
        
        controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(title, size=10, color=CHART_COLORS['text_secondary']),
                        ft.Text(str(curr_val), size=18, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(change_text, size=10, color=change_color),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2
                ),
                expand=True,
                bgcolor=CHART_COLORS['surface'],
                border_radius=8,
                padding=ft.padding.all(8),
                border=ft.border.all(1, CHART_COLORS['border'])
            )
        )
    
    return ft.Row(controls=controls, spacing=8, expand=True)

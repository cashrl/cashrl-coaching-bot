"""
RLBotPro - Evolution Charts
Gráficos de evolução de performance ao longo do tempo.
Migrado de Flet para NiceGUI.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from nicegui import ui

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
) -> ui.element:
    """
    Cria um gráfico de evolução para uma stat específica usando ECharts.

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
        values.append(value if value else 0)
        # Label: data ou índice
        if "date" in item and item["date"]:
            try:
                date_str = str(item["date"])[:10]
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                labels.append(dt.strftime("%d/%m"))
            except (ValueError, TypeError):
                labels.append(str(i + 1))
        else:
            labels.append(str(i + 1))

    # Valor atual
    current_value = values[-1] if values else 0

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

    # Configuração do ECharts
    chart_option = {
        'backgroundColor': 'transparent',
        'grid': {
            'left': '8%',
            'right': '5%',
            'top': '8%',
            'bottom': '15%',
        },
        'tooltip': {
            'trigger': 'axis',
            'backgroundColor': CHART_COLORS['surface'],
            'borderColor': CHART_COLORS['border'],
            'textStyle': {
                'color': CHART_COLORS['text'],
                'fontSize': 11
            },
        },
        'xAxis': {
            'type': 'category',
            'data': labels,
            'axisLine': {'lineStyle': {'color': CHART_COLORS['border']}},
            'axisLabel': {
                'color': CHART_COLORS['text_secondary'],
                'fontSize': 9,
                'rotate': 0 if len(labels) <= 10 else 45
            },
            'axisTick': {'show': False},
        },
        'yAxis': {
            'type': 'value',
            'axisLine': {'show': False},
            'splitLine': {
                'lineStyle': {'color': CHART_COLORS['border'], 'type': 'dashed'}
            },
            'axisLabel': {
                'color': CHART_COLORS['text_secondary'],
                'fontSize': 9
            },
        },
        'series': [{
            'name': title,
            'type': 'line',
            'data': values,
            'smooth': True,
            'symbol': 'circle',
            'symbolSize': 6,
            'lineStyle': {
                'color': color,
                'width': 2.5
            },
            'itemStyle': {
                'color': color,
                'borderWidth': 2,
                'borderColor': '#fff'
            },
            'areaStyle': {
                'color': {
                    'type': 'linear',
                    'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                    'colorStops': [
                        {'offset': 0, 'color': color + '40'},
                        {'offset': 1, 'color': color + '05'}
                    ]
                }
            },
        }]
    }

    # Container com header + gráfico
    container = ui.column().classes('w-full')
    with container:
        # Header
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-0'):
                ui.label(title).classes(
                    'text-xs font-semibold'
                ).style(f'color: {CHART_COLORS["text_secondary"]}')
                ui.label(f'{current_value:.1f}{unit}').classes(
                    'text-2xl font-bold'
                ).style(f'color: {color}')
            ui.label(variation_text).classes(
                'text-xs font-semibold px-2 py-1 rounded-md'
            ).style(f'color: {variation_color}; background: {variation_color}20')

        # Gráfico ECharts
        ui.echart(chart_option).classes('w-full').style('height: 150px;')

    return container


def _empty_chart(title: str) -> ui.element:
    """Retorna um gráfico vazio."""
    container = ui.column().classes(
        'w-full items-center justify-center'
    ).style(
        f'height: 200px; background: {CHART_COLORS["surface"]}; '
        f'border-radius: 10px; border: 1px solid {CHART_COLORS["border"]}'
    )
    with container:
        ui.label(title).classes(
            'text-xs font-semibold'
        ).style(f'color: {CHART_COLORS["text_secondary"]}')
        ui.icon('show_chart', size='32px').style(
            f'color: {CHART_COLORS["text_secondary"]}'
        )
        ui.label('Sem dados suficientes').classes(
            'text-xs'
        ).style(f'color: {CHART_COLORS["text_secondary"]}')
    return container


def create_stats_grid(match_history: List[Dict]) -> ui.element:
    """
    Cria um grid de stats comparativo (atual vs anterior).
    """
    container = ui.row().classes('w-full gap-2')

    if not match_history or len(match_history) < 2:
        with container:
            ui.label('Histórico insuficiente para comparação').classes(
                'text-xs'
            ).style(f'color: {CHART_COLORS["text_secondary"]}')
        return container

    current = match_history[-1]
    previous = match_history[-2]

    stats = [
        ("Gols", "goals", CHART_COLORS['primary']),
        ("Assists", "assists", CHART_COLORS['cyan']),
        ("Saves", "saves", CHART_COLORS['success']),
        ("Shots", "shots", CHART_COLORS['warning']),
        ("Score", "score", CHART_COLORS['secondary']),
    ]

    with container:
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

            with ui.card().classes('flex-1 items-center').style(
                f'background: {CHART_COLORS["surface"]}; border-radius: 8px; '
                f'border: 1px solid {CHART_COLORS["border"]}; padding: 8px;'
            ):
                ui.label(title).classes('text-xs').style(
                    f'color: {CHART_COLORS["text_secondary"]}'
                )
                ui.label(str(curr_val)).classes('text-lg font-bold').style(
                    f'color: {color}'
                )
                ui.label(change_text).classes('text-xs').style(
                    f'color: {change_color}'
                )

    return container

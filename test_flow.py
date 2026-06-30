"""
RLBotPro - Test Script
Testa o fluxo completo de análise usando dados da API do Ballchasing.
"""
import sys
import json
from pathlib import Path

# Adicionar diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

from bot.uploader import BallchasingUploader
from bot.analyzer import ReplayAnalyzer
from bot.comparer import ProComparer
from database import Database


def test_full_flow():
    """Testa o fluxo completo: buscar replay -> analisar -> comparar -> salvar."""
    print("=" * 60)
    print("RLBotPro - Teste do Fluxo Completo")
    print("=" * 60)

    # 1. Carregar config
    config_path = Path("config.json")
    if not config_path.exists():
        print("ERRO: config.json nao encontrado!")
        return False

    with open(config_path, 'r') as f:
        config = json.load(f)

    token = config.get('ballchasing_token', '')
    player_name = config.get('player_name', '')
    pro_name = config.get('pro_to_study', 'Zen')

    print(f"\n[1/5] Configuracao:")
    print(f"  Token: {token[:8]}...{token[-4:]}" if len(token) > 12 else f"  Token: {token}")
    print(f"  Jogador: {player_name}")
    print(f"  Pro estudado: {pro_name}")

    # 2. Inicializar componentes
    print(f"\n[2/5] Inicializando componentes...")
    uploader = BallchasingUploader(token)
    analyzer = ReplayAnalyzer(player_name)
    db = Database("data/history.db")
    comparer = ProComparer(uploader, analyzer, db)
    print("  OK - Todos os componentes inicializados")

    # 3. Buscar replay de pro recente via API
    print(f"\n[3/5] Buscando replay de pro via API...")
    playlist = config.get('playlists', ['ranked-doubles'])[0]
    replays = uploader.get_pro_replays(playlist, count=5)

    if not replays:
        print(f"  AVISO: Nenhum replay de pro encontrado para {playlist}")
        print(f"  Tentando ranked-standard...")
        replays = uploader.get_pro_replays('ranked-standard', count=5)

    if not replays:
        print("  ERRO: Nenhum replay encontrado em nenhuma playlist!")
        return False

    print(f"  Encontrados {len(replays)} replays")

    # Pegar o primeiro replay
    replay_summary = replays[0]
    replay_id = replay_summary.get('id')
    replay_name = replay_summary.get('name', 'Sem nome')
    print(f"  Replay selecionado: {replay_name} (ID: {replay_id})")

    # 4. Buscar detalhes e analisar
    print(f"\n[4/5] Buscando detalhes e analisando replay...")
    replay_data = uploader.get_replay_details(replay_id)

    if not replay_data:
        print("  ERRO: Falha ao buscar detalhes do replay!")
        return False

    print(f"  Detalhes obtidos com sucesso")

    # Analisar replay
    player_stats = analyzer.analyze_replay(replay_data)

    if not player_stats:
        # Tentar com nome do pro (pois o replay e de pro)
        print(f"  Jogador '{player_name}' nao encontrado, tentando com '{pro_name}'...")
        pro_analyzer = ReplayAnalyzer(pro_name)
        player_stats = pro_analyzer.analyze_replay(replay_data)

    if not player_stats:
        # Buscar qualquer jogador disponivel no replay
        print(f"  Pro '{pro_name}' tambem nao encontrado, buscando qualquer jogador...")
        all_players = []
        for team in ['blue', 'orange']:
            team_players = replay_data.get(team, {}).get('players', [])
            for p in team_players:
                all_players.append(p.get('name', ''))
        print(f"  Jogadores no replay: {all_players}")
        if all_players:
            fallback_analyzer = ReplayAnalyzer(all_players[0])
            player_stats = fallback_analyzer.analyze_replay(replay_data)

    if not player_stats:
        print("  ERRO: Falha ao analisar replay!")
        return False

    print(f"  Analise concluida!")
    print(f"  Stats extraidas:")
    print(f"    Score: {player_stats.get('score', 0)}")
    print(f"    Goals: {player_stats.get('goals', 0)}")
    print(f"    Assists: {player_stats.get('assists', 0)}")
    print(f"    Saves: {player_stats.get('saves', 0)}")
    print(f"    Boost avg: {player_stats.get('boost_avg', 0):.1f}")
    print(f"    Avg speed: {player_stats.get('avg_speed', 0):.1f}")
    print(f"    Playlist: {player_stats.get('playlist', 'N/A')}")
    print(f"    Result: {player_stats.get('result', 'N/A')}")

    # 5. Comparar com baseline (simplificado - sem buscar 200 replays)
    print(f"\n[5/5] Comparando com baseline...")
    try:
        # Verificar se baseline ja existe no banco
        existing_baseline = db.get_baseline(playlist, pro_name)
        if existing_baseline:
            print(f"  Baseline encontrada no banco ({existing_baseline['sample_size']} samples)")
            comparison = comparer.compare(player_stats, existing_baseline['averages'])
            proximity_score = comparison.get('score', 0)
            player_stats['proximity_score'] = proximity_score
            print(f"  Score de proximidade: {proximity_score:.1f}%")
            if comparison.get('tips'):
                print(f"  Dicas:")
                for tip in comparison['tips']:
                    print(f"    - {tip}")
        else:
            print("  Baseline nao encontrada no banco (pulando comparacao)")
            print("  Use 'Atualizar Baseline' no dashboard para buscar dados de pros")
            player_stats['proximity_score'] = 0
    except Exception as e:
        print(f"  ERRO na comparacao: {e}")
        player_stats['proximity_score'] = 0

    # Salvar no banco
    print(f"\n  Salvando no banco de dados...")
    match_id = db.insert_match(player_stats)
    if match_id:
        print(f"  Salvo com sucesso! Match ID: {match_id}")
    else:
        print(f"  Replay ja existente no banco (duplicado) ou erro ao salvar")

    # Verificar no banco
    print(f"\n  Verificando dados no banco...")
    recent_matches = db.get_matches(limit=3)
    print(f"  Total de partidas no banco: {len(recent_matches)}")
    for m in recent_matches:
        print(f"    - {m.get('date', '')[:10]} | {m.get('result', '?')} | Score: {m.get('score', 0)} | Proximidade: {m.get('proximity_score', 0) or 0:.1f}%")

    db.close()

    print(f"\n{'=' * 60}")
    print("TESTE CONCLUIDO COM SUCESSO!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_full_flow()
    sys.exit(0 if success else 1)

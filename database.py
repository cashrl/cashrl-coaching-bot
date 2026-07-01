"""
RLBotPro - Database Module
Gerencia o SQLite para histórico de partidas e baselines de pros.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """Classe principal para gerenciar o banco de dados SQLite."""

    def __init__(self, db_path: str = "data/history.db"):
        """
        Inicializa a conexão com o banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados
        """
        self.db_path = db_path
        self._ensure_directory()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _ensure_directory(self) -> None:
        """Garante que o diretório do banco existe."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _create_tables(self) -> None:
        """Cria as tabelas necessárias se não existirem."""
        cursor = self.conn.cursor()
        
        # Tabela de partidas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id TEXT UNIQUE,
                playlist TEXT,
                date TIMESTAMP,
                score INTEGER,
                goals INTEGER,
                assists INTEGER,
                saves INTEGER,
                result TEXT,
                opponent_rank TEXT,
                my_rank TEXT,
                boost_avg REAL,
                time_zero_boost REAL,
                big_pads INTEGER,
                small_pads INTEGER,
                avg_distance_to_ball REAL,
                avg_speed REAL,
                time_supersonic REAL,
                shooting_pct REAL,
                proximity_score REAL,
                raw_json TEXT
            )
        """)
        
        # Tabela de baselines
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist TEXT,
                pro_name TEXT,
                sample_size INTEGER,
                averages_json TEXT,
                updated_at TIMESTAMP,
                UNIQUE(playlist, pro_name)
            )
        """)
        
        self.conn.commit()

    def insert_match(self, match_data: Dict[str, Any]) -> Optional[int]:
        """
        Insere uma nova partida no banco de dados.
        
        Args:
            match_data: Dicionário com os dados da partida
            
        Returns:
            ID da partida inserida ou None se já existir
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO matches (
                    replay_id, playlist, date, score, goals, assists, saves,
                    result, opponent_rank, my_rank, boost_avg, time_zero_boost,
                    big_pads, small_pads, avg_distance_to_ball, avg_speed,
                    time_supersonic, shooting_pct, proximity_score, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data.get('replay_id'),
                match_data.get('playlist'),
                match_data.get('date', datetime.now().isoformat()),
                match_data.get('score'),
                match_data.get('goals'),
                match_data.get('assists'),
                match_data.get('saves'),
                match_data.get('result'),
                match_data.get('opponent_rank'),
                match_data.get('my_rank'),
                match_data.get('boost_avg'),
                match_data.get('time_zero_boost'),
                match_data.get('big_pads'),
                match_data.get('small_pads'),
                match_data.get('avg_distance_to_ball'),
                match_data.get('avg_speed'),
                match_data.get('time_supersonic'),
                match_data.get('shooting_pct'),
                match_data.get('proximity_score'),
                json.dumps(match_data.get('raw_json', {}))
            ))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Erro ao inserir partida: {e}")
            return None

    def get_matches(self, limit: int = 50, playlist: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca partidas do banco de dados.
        
        Args:
            limit: Limite de resultados
            playlist: Filtrar por playlist específica
            
        Returns:
            Lista de partidas
        """
        cursor = self.conn.cursor()
        if playlist:
            cursor.execute(
                "SELECT * FROM matches WHERE playlist = ? ORDER BY date DESC LIMIT ?",
                (playlist, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM matches ORDER BY date DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_today_matches(self) -> List[Dict[str, Any]]:
        """Busca partidas de hoje."""
        cursor = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT * FROM matches WHERE date LIKE ? ORDER BY date DESC",
            (f"{today}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_match_by_replay_id(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma partida pelo replay_id.
        
        Args:
            replay_id: ID único do replay
            
        Returns:
            Dados da partida ou None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM matches WHERE replay_id = ?", (replay_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_baseline(self, playlist: str, pro_name: Optional[str], 
                      sample_size: int, averages: Dict[str, Any]) -> bool:
        """
        Salva ou atualiza uma baseline de pro/jogador.
        
        Args:
            playlist: Nome da playlist
            pro_name: Nome do pro (None para média geral)
            sample_size: Quantidade de replays analisados
            averages: Dicionário com médias e desvios padrão
            
        Returns:
            True se salvou com sucesso
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO baselines (playlist, pro_name, sample_size, averages_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                playlist,
                pro_name,
                sample_size,
                json.dumps(averages),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao salvar baseline: {e}")
            return False

    def get_baseline(self, playlist: str, pro_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Busca uma baseline do banco de dados.
        
        Args:
            playlist: Nome da playlist
            pro_name: Nome do pro (None para média geral)
            
        Returns:
            Dados da baseline ou None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM baselines WHERE playlist = ? AND pro_name IS ?",
            (playlist, pro_name)
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['averages'] = json.loads(result['averages_json'])
            return result
        return None

    def get_proximity_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca histórico de scores de proximidade.
        
        Args:
            limit: Limite de resultados
            
        Returns:
            Lista com data e score de proximidade
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT date, proximity_score FROM matches WHERE proximity_score IS NOT NULL ORDER BY date DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def clean_old_baselines(self) -> int:
        """
        Remove baselines com formato antigo (flat floats) onde os valores
        das stats são floats em vez de dicts {mean, std, min, max}.
        Essas baselines serão re-fetchadas automaticamente no próximo uso.

        Returns:
            Quantidade de baselines removidas
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, playlist, pro_name, averages_json FROM baselines")
        rows = cursor.fetchall()

        removed = 0
        for row in rows:
            try:
                averages = json.loads(row['averages_json'])
                if not averages:
                    continue
                # Check: at least one stat value should be a dict with 'mean'
                has_dict_format = any(
                    isinstance(v, dict) and 'mean' in v
                    for v in averages.values()
                )
                if not has_dict_format:
                    # Flat format (all floats) — delete so it gets re-fetched
                    cursor.execute("DELETE FROM baselines WHERE id = ?", (row['id'],))
                    removed += 1
                    print(f"Baseline antiga removida: {row['playlist']} / {row['pro_name']}")
            except (json.JSONDecodeError, TypeError):
                # Corrupted JSON — delete it too
                cursor.execute("DELETE FROM baselines WHERE id = ?", (row['id'],))
                removed += 1
                print(f"Baseline corrompida removida: {row['playlist']} / {row['pro_name']}")

        if removed > 0:
            self.conn.commit()
            print(f"{removed} baseline(s) antiga(s) removida(s). Será re-fetchada no próximo uso.")

        return removed

    def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()

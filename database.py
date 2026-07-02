"""
RLBotPro - Database Module
Gerencia o SQLite para historico de partidas e baselines de pros.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """Classe principal para gerenciar o banco de dados SQLite."""

    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        self._ensure_directory()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _ensure_directory(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pro_moment_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                pro_name TEXT NOT NULL,
                playlist TEXT,
                dominant_pattern TEXT,
                frequency REAL,
                sample_moments INTEGER,
                details_json TEXT,
                updated_at TIMESTAMP,
                UNIQUE(category, pro_name, playlist)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_moments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id TEXT,
                player_name TEXT,
                timestamp REAL,
                category TEXT,
                severity TEXT,
                context_json TEXT,
                analyzed INTEGER DEFAULT 0,
                coaching_text TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rank_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rl_nickname TEXT NOT NULL,
                platform TEXT NOT NULL DEFAULT 'epic',
                player_name TEXT,
                rank_data_json TEXT,
                fetched_at TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(rl_nickname, platform)
            )
        """)

        self.conn.commit()

    def insert_match(self, match_data: Dict[str, Any]) -> Optional[int]:
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
        cursor = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT * FROM matches WHERE date LIKE ? ORDER BY date DESC",
            (f"{today}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_match_by_replay_id(self, replay_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM matches WHERE replay_id = ?", (replay_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_baseline(self, playlist: str, pro_name: Optional[str],
                      sample_size: int, averages: Dict[str, Any]) -> bool:
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
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT date, proximity_score FROM matches WHERE proximity_score IS NOT NULL ORDER BY date DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def clean_old_baselines(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, playlist, pro_name, averages_json FROM baselines")
        rows = cursor.fetchall()

        removed = 0
        for row in rows:
            try:
                averages = json.loads(row['averages_json'])
                if not averages:
                    continue
                has_dict_format = any(
                    isinstance(v, dict) and 'mean' in v
                    for v in averages.values()
                )
                if not has_dict_format:
                    cursor.execute("DELETE FROM baselines WHERE id = ?", (row['id'],))
                    removed += 1
                    print(f"Baseline antiga removida: {row['playlist']} / {row['pro_name']}")
            except (json.JSONDecodeError, TypeError):
                cursor.execute("DELETE FROM baselines WHERE id = ?", (row['id'],))
                removed += 1
                print(f"Baseline corrompida removida: {row['playlist']} / {row['pro_name']}")

        if removed > 0:
            self.conn.commit()
            print(f"{removed} baseline(s) antiga(s) removida(s).")

        return removed

    # ==================================================================
    # MOMENT BASELINES
    # ==================================================================

    def save_moment_baseline(
        self,
        category: str,
        pro_name: str,
        playlist: Optional[str],
        dominant_pattern: str,
        frequency: float,
        sample_moments: int,
        details: Dict[str, Any],
    ) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pro_moment_baselines
                    (category, pro_name, playlist, dominant_pattern,
                     frequency, sample_moments, details_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category, pro_name, playlist, dominant_pattern,
                frequency, sample_moments, json.dumps(details),
                datetime.now().isoformat(),
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao salvar moment baseline: {e}")
            return False

    def get_moment_baseline(
        self, category: str, pro_name: str, playlist: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM pro_moment_baselines WHERE category=? AND pro_name=? AND playlist IS ?",
            (category, pro_name, playlist),
        )
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["details"] = json.loads(d["details_json"])
            return d
        return None

    def get_all_moment_baselines(
        self, pro_name: Optional[str] = None, playlist: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        clauses, params = [], []
        if pro_name:
            clauses.append("pro_name = ?")
            params.append(pro_name)
        if playlist:
            clauses.append("playlist IS ?")
            params.append(playlist)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        cursor.execute(
            f"SELECT * FROM pro_moment_baselines{where} ORDER BY category, pro_name",
            tuple(params),
        )
        rows = []
        for row in cursor.fetchall():
            d = dict(row)
            d["details"] = json.loads(d["details_json"])
            rows.append(d)
        return rows

    # ==================================================================
    # DETECTED MOMENTS
    # ==================================================================

    def insert_detected_moment(
        self,
        replay_id: str,
        player_name: str,
        timestamp: float,
        category: str,
        severity: str,
        context: Dict[str, Any],
    ) -> Optional[int]:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO detected_moments
                   (replay_id, player_name, timestamp, category, severity, context_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (replay_id, player_name, timestamp, category, severity, json.dumps(context)),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Erro ao inserir momento: {e}")
            return None

    def get_unanalyzed_moments(self, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM detected_moments WHERE analyzed=0 ORDER BY timestamp LIMIT ?",
            (limit,),
        )
        rows = []
        for row in cursor.fetchall():
            d = dict(row)
            d["context"] = json.loads(d["context_json"])
            rows.append(d)
        return rows

    def mark_moment_analyzed(self, moment_id: int, coaching_text: str) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE detected_moments SET analyzed=1, coaching_text=? WHERE id=?",
                (coaching_text, moment_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao atualizar momento: {e}")
            return False

    def get_moments_by_replay(self, replay_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM detected_moments WHERE replay_id=? ORDER BY timestamp",
            (replay_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================================================================
    # ANALYTICS: ERROR PATTERNS BY RANK
    # ==================================================================

    def get_error_patterns_by_rank(self, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.opponent_rank, dm.category,
                   COUNT(*) as count,
                   AVG(CASE dm.severity WHEN 'alta' THEN 3 WHEN 'media' THEN 2 ELSE 1 END) as avg_severity
            FROM detected_moments dm
            JOIN matches m ON dm.replay_id = m.replay_id
            WHERE m.opponent_rank IS NOT NULL AND m.opponent_rank != ''
            GROUP BY m.opponent_rank, dm.category
            ORDER BY m.opponent_rank, count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_wins_losses_by_rank(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT opponent_rank,
                   SUM(CASE result WHEN 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE result WHEN 'loss' THEN 1 ELSE 0 END) as losses,
                   COUNT(*) as total
            FROM matches
            WHERE opponent_rank IS NOT NULL AND opponent_rank != ''
            GROUP BY opponent_rank
            ORDER BY total DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    # ==================================================================
    # ANALYTICS: STREAK / TILT DETECTOR
    # ==================================================================

    def detect_lose_streak(self, min_streak: int = 2) -> Optional[Dict[str, Any]]:
        matches = self.get_matches(limit=20)
        if not matches:
            return None

        streak_ids = []
        streak_dates = []
        for m in matches:
            if m.get('result') == 'loss':
                streak_ids.append(m.get('replay_id'))
                streak_dates.append(m.get('date', ''))
            else:
                break

        if len(streak_ids) >= min_streak:
            return {
                'streak_length': len(streak_ids),
                'match_ids': streak_ids,
                'first_loss_date': streak_dates[-1] if streak_dates else '',
                'last_loss_date': streak_dates[0] if streak_dates else '',
            }
        return None

    def detect_quality_drop(self, window: int = 5) -> Optional[Dict[str, Any]]:
        """
        Detecta queda de qualidade apos derrotas.
        get_matches() retorna em ordem DESC (mais recente primeiro).
        - matches[:loss_start] = partidas MAIS RECENTES (apos as derrotas)
        - matches[loss_start+N:] = partidas MAIS ANTIGAS (antes das derrotas)
        """
        matches = self.get_matches(limit=window * 3)
        if len(matches) < window * 2:
            return None

        loss_start = None
        for i, m in enumerate(matches):
            if m.get('result') == 'loss':
                if loss_start is None:
                    loss_start = i
            else:
                if loss_start is not None and (i - loss_start) >= 2:
                    break
                loss_start = None

        if loss_start is None:
            return None

        # DESC order: higher indices = older matches (before losses)
        older = matches[loss_start + 2:loss_start + 2 + window]
        newer = matches[:loss_start]

        if not older or not newer:
            return None

        before_scores = [m.get('proximity_score', 50) or 50 for m in older]
        after_scores = [m.get('proximity_score', 50) or 50 for m in newer]

        before_avg = sum(before_scores) / len(before_scores)
        after_avg = sum(after_scores) / len(after_scores)
        drop_pct = before_avg - after_avg

        return {
            'before_avg': round(before_avg, 1),
            'after_avg': round(after_avg, 1),
            'drop_pct': round(drop_pct, 1),
            'suggesting_pause': drop_pct > 10,
        }

    # ==================================================================
    # HEATMAP: PLAYER POSITIONS
    # ==================================================================

    def get_player_positions(self, limit: int = 500) -> List[List[float]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT raw_json FROM matches
            WHERE raw_json IS NOT NULL
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        positions = []
        for row in cursor.fetchall():
            try:
                data = json.loads(row['raw_json'])
                pos_sample = data.get('positions_sample', [])
                positions.extend(pos_sample)
            except (json.JSONDecodeError, TypeError):
                continue
        return positions

    # ==================================================================
    # RANK CACHE
    # ==================================================================

    def get_rank_cache(self, rl_nickname: str, platform: str = "epic") -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM rank_cache WHERE rl_nickname = ? AND platform = ?",
            (rl_nickname, platform),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_rank_cache(
        self,
        rl_nickname: str,
        platform: str,
        player_name: str,
        rank_data: Dict[str, Any],
        ttl_seconds: int = 1200,
    ) -> bool:
        """Salva cache de rank com TTL (default 20 min)."""
        try:
            now = datetime.now()
            expires = now.__class__.fromtimestamp(now.timestamp() + ttl_seconds)
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rank_cache
                    (rl_nickname, platform, player_name, rank_data_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rl_nickname,
                platform,
                player_name,
                json.dumps(rank_data),
                now.isoformat(),
                expires.isoformat(),
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao salvar cache de rank: {e}")
            return False

    def close(self) -> None:
        if self.conn:
            self.conn.close()

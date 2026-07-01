"""
Teste automatizado de navegação — verifica que _refresh_data()
não causa crash quando chamado de qualquer página.

Usa NiceGUI headless (sem pywebview) pra poder rodar no terminal.
"""
import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Rodar NiceGUI em modo headless (sem janela)
os.environ['NICEGUI_HEADLESS'] = '1'

from nicegui import app, ui
from database import Database
from dashboard.ui import Dashboard


def main():
    db = Database("data/history.db")
    config = {
        'auto_start_watcher': True,
        'notifications': False,
        'auto_upload': False,
        'player_name': 'TestPlayer',
        'pro_to_study': 'Zen',
    }
    dashboard = Dashboard(db, config, None)

    errors = []

    @ui.page('/')
    def index():
        nonlocal errors
        dashboard.build()

        # Test 1: Dashboard refresh works
        try:
            dashboard.current_page = 0
            dashboard._refresh_data()
            print("[PASS] Test 1: _refresh_data() on Dashboard")
        except Exception as e:
            errors.append(f"Test 1: {e}")
            print(f"[FAIL] Test 1: {e}")

        # Test 2: Navigate to Análises
        try:
            dashboard._on_nav_click(1)
            assert dashboard.current_page == 1
            print("[PASS] Test 2: Navigate to Análises")
        except Exception as e:
            errors.append(f"Test 2: {e}")
            print(f"[FAIL] Test 2: {e}")

        # Test 3: _refresh_data() on Análises (should skip safely)
        try:
            dashboard._refresh_data()
            print("[PASS] Test 3: _refresh_data() on Análises (skip)")
        except Exception as e:
            errors.append(f"Test 3: {e}")
            print(f"[FAIL] Test 3: {e}")

        # Test 4: Navigate to Histórico
        try:
            dashboard._on_nav_click(2)
            assert dashboard.current_page == 2
            print("[PASS] Test 4: Navigate to Histórico")
        except Exception as e:
            errors.append(f"Test 4: {e}")
            print(f"[FAIL] Test 4: {e}")

        # Test 5: _refresh_data() on Histórico (should skip)
        try:
            dashboard._refresh_data()
            print("[PASS] Test 5: _refresh_data() on Histórico (skip)")
        except Exception as e:
            errors.append(f"Test 5: {e}")
            print(f"[FAIL] Test 5: {e}")

        # Test 6: Navigate to Config
        try:
            dashboard._on_nav_click(3)
            assert dashboard.current_page == 3
            print("[PASS] Test 6: Navigate to Config")
        except Exception as e:
            errors.append(f"Test 6: {e}")
            print(f"[FAIL] Test 6: {e}")

        # Test 7: _refresh_data() on Config (should skip)
        try:
            dashboard._refresh_data()
            print("[PASS] Test 7: _refresh_data() on Config (skip)")
        except Exception as e:
            errors.append(f"Test 7: {e}")
            print(f"[FAIL] Test 7: {e}")

        # Test 8: _save_settings() from Config page (THE original crash)
        try:
            dashboard.switch_monitoring.value = True
            dashboard.switch_notifications.value = False
            dashboard.switch_auto_upload.value = False
            dashboard._save_settings()
            print("[PASS] Test 8: _save_settings() from Config (was the crash)")
        except Exception as e:
            errors.append(f"Test 8: {e}")
            print(f"[FAIL] Test 8: {e}")

        # Test 9: Navigate back to Dashboard
        try:
            dashboard._on_nav_click(0)
            assert dashboard.current_page == 0
            print("[PASS] Test 9: Navigate back to Dashboard")
        except Exception as e:
            errors.append(f"Test 9: {e}")
            print(f"[FAIL] Test 9: {e}")

        # Test 10: Dashboard refresh works again after round-trip
        try:
            dashboard._refresh_data()
            print("[PASS] Test 10: Dashboard refresh after round-trip")
        except Exception as e:
            errors.append(f"Test 10: {e}")
            print(f"[FAIL] Test 10: {e}")

        # Test 11: Full cycle 0->1->2->3->3->2->1->0
        try:
            for page in [0, 1, 2, 3, 3, 2, 1, 0]:
                dashboard._on_nav_click(page)
                dashboard._refresh_data()
            print("[PASS] Test 11: Full navigation cycle")
        except Exception as e:
            errors.append(f"Test 11: {e}")
            print(f"[FAIL] Test 11: {e}")

        # Summary
        print("\n" + "=" * 50)
        if errors:
            print(f"FAILED: {len(errors)} test(s) failed")
            for err in errors:
                print(f"  - {err}")
        else:
            print("ALL 11 TESTS PASSED!")
        print("=" * 50)

        db.close()
        app.shutdown()

    ui.run(reload=False)


if __name__ == "__main__":
    main()

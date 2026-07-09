import sqlite3

from my_crew.tools.memory_tool import memory_tool


def run_tool(**kwargs) -> str:
    return memory_tool.run(**kwargs)


class TestMemoryTool:
    def test_save_and_get(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(tmp_path / "mem.db"))
        assert "saved" in run_tool(action="save", key="topic", value="AI agents")
        assert run_tool(action="get", key="topic") == "AI agents"

    def test_save_overwrites_existing_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(tmp_path / "mem.db"))
        run_tool(action="save", key="topic", value="first")
        run_tool(action="save", key="topic", value="second")
        assert run_tool(action="get", key="topic") == "second"

    def test_get_missing_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(tmp_path / "mem.db"))
        assert run_tool(action="get", key="nothing") == "No memory found."

    def test_delete(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(tmp_path / "mem.db"))
        run_tool(action="save", key="topic", value="AI agents")
        assert "deleted" in run_tool(action="delete", key="topic")
        assert run_tool(action="get", key="topic") == "No memory found."
        assert run_tool(action="delete", key="topic") == "Key not found."

    def test_invalid_action(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(tmp_path / "mem.db"))
        assert run_tool(action="explode", key="x") == "Invalid action."

    def test_memory_persists_across_connections(self, tmp_path, monkeypatch):
        db = tmp_path / "mem.db"
        monkeypatch.setenv("MY_CREW_MEMORY_DB", str(db))
        run_tool(action="save", key="persistent", value="still here")

        rows = sqlite3.connect(db).execute(
            "SELECT key, value FROM memory"
        ).fetchall()
        assert rows == [("persistent", "still here")]

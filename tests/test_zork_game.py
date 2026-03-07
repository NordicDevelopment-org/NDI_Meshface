from meshdash.games.zork import ZorkGame


def test_zork_game_happy_path_reaches_victory():
    game = ZorkGame()

    result = game.try_handle_message(
        text="zork",
        from_id="!49b5dff0",
        to_id="!02ed9b7c",
        local_node_id="!02ed9b7c",
        now_unix=1710001240,
        enabled=True,
    )
    assert result.handled is True
    assert result.command_name == "zork"
    assert "trailhead" in str(result.reply_text).lower()
    assert game.has_active_session("!49b5dff0") is True

    for step in ("north", "take key", "west", "open gate", "north", "take beacon"):
        result = game.try_handle_message(
            text=step,
            from_id="!49b5dff0",
            to_id="!02ed9b7c",
            local_node_id="!02ed9b7c",
            now_unix=1710001240,
            enabled=True,
        )
        assert result.handled is True
        assert result.command_name == "zork"

    assert "victory" in str(result.reply_text).lower()

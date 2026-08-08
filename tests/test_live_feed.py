from app.paper.live_feed import LiveFeed


def test_live_feed_returns_snapshot():

    feed = LiveFeed()

    snapshot = {
        "15m": [],
        "1h": [],
        "4h": [],
    }

    feed.update(
        snapshot
    )

    assert feed.has_next()

    result = feed.next()

    assert result == snapshot

    assert not feed.has_next()
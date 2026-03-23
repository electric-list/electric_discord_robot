import bot_core


class DummyRole:
    def __init__(self, role_id: int):
        self.id = role_id


class DummyMember:
    def __init__(self, role_ids):
        self.roles = [DummyRole(role_id) for role_id in role_ids]


def test_princess_role_settings_roundtrip():
    assert bot_core.get_princess_role_id() is None

    bot_core.set_princess_role(12345)
    assert bot_core.get_princess_role_id() == 12345

    # Ensure persisted settings include princess role.
    loaded = bot_core.load_bot_settings()
    assert loaded["princess_role_id"] == 12345


def test_is_princess_member_uses_configured_role():
    bot_core.set_princess_role(900)

    assert bot_core.is_princess_member(DummyMember([100, 900])) is True
    assert bot_core.is_princess_member(DummyMember([100, 200])) is False


def test_pending_views_store_princess_metadata():
    bot_core.add_pending_request_view(
        message_id=1,
        requester_mention="@princess",
        requested_amount=50.0,
        target_text="",
        request_note="n",
        reimbursement_item=None,
        target_user_id=None,
        princess_user_id=111,
        princess_display_name="Princess A",
    )
    bot_core.add_pending_sub_claim_view(
        message_id=2,
        requester_id=222,
        amount=60.0,
        note="proof",
        platform="cashapp",
        princess_user_id=111,
        princess_display_name="Princess A",
    )
    bot_core.add_pending_game_view(
        message_id=3,
        target_user_id=222,
        amount=25.0,
        source="dice",
        princess_user_id=111,
        princess_display_name="Princess A",
    )

    pending = bot_core.load_pending_views()

    assert pending["request"]["1"]["princess_user_id"] == 111
    assert pending["request"]["1"]["princess_display_name"] == "Princess A"

    assert pending["sub_claim"]["2"]["princess_user_id"] == 111
    assert pending["sub_claim"]["2"]["princess_display_name"] == "Princess A"

    assert pending["game"]["3"]["princess_user_id"] == 111
    assert pending["game"]["3"]["princess_display_name"] == "Princess A"

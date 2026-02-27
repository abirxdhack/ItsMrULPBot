import logging

from telethon.tl.types import (
    KeyboardButtonUrl,
    KeyboardButtonCallback,
    KeyboardButtonWebView,
    KeyboardButtonSwitchInline,
    KeyboardButtonUrlAuth,
    KeyboardButtonCopy,
    KeyboardButtonRow,
    KeyboardButtonRequestPeer,
    KeyboardButtonRequestPhone,
    KeyboardButtonRequestGeoLocation,
    KeyboardButtonGame,
    KeyboardButtonBuy,
    KeyboardButtonSimpleWebView,
    InputKeyboardButtonUserProfile,
    ReplyInlineMarkup,
)

LOGGER = logging.getLogger(__name__)


class SmartButtons:
    def __init__(self):
        self._button = []
        self._header_button = []
        self._footer_button = []

    def button(self, text, callback_data=None, url=None, pay=None, web_app=None,
               login_url=None, switch_inline_query=None,
               switch_inline_query_current_chat=None,
               switch_inline_query_chosen_chat=None, copy_text=None,
               callback_game=None, request_peer=None, request_phone=None,
               request_location=None, simple_web_view=None, user_profile=None,
               position=None):
        try:
            if callback_data is not None:
                encoded = callback_data.encode() if isinstance(callback_data, str) else callback_data
                btn = KeyboardButtonCallback(text=text, data=encoded)
            elif url is not None:
                btn = KeyboardButtonUrl(text=text, url=url)
            elif pay:
                btn = KeyboardButtonBuy(text=text)
            elif web_app is not None:
                u = web_app.url if hasattr(web_app, 'url') else web_app
                btn = KeyboardButtonWebView(text=text, url=u)
            elif simple_web_view is not None:
                btn = KeyboardButtonSimpleWebView(text=text, url=simple_web_view)
            elif login_url is not None:
                if isinstance(login_url, dict):
                    btn = KeyboardButtonUrlAuth(text=text, **login_url)
                else:
                    btn = KeyboardButtonUrlAuth(text=text, url=login_url, button_id=0)
            elif switch_inline_query is not None:
                btn = KeyboardButtonSwitchInline(text=text, query=switch_inline_query, same_peer=False)
            elif switch_inline_query_current_chat is not None:
                btn = KeyboardButtonSwitchInline(text=text, query=switch_inline_query_current_chat, same_peer=True)
            elif switch_inline_query_chosen_chat is not None:
                q = getattr(switch_inline_query_chosen_chat, 'query', str(switch_inline_query_chosen_chat))
                pt = getattr(switch_inline_query_chosen_chat, 'peer_types', None)
                btn = KeyboardButtonSwitchInline(text=text, query=q, same_peer=False, peer_types=pt)
            elif copy_text is not None:
                v = copy_text.text if hasattr(copy_text, 'text') else str(copy_text)
                btn = KeyboardButtonCopy(text, v)
            elif callback_game:
                btn = KeyboardButtonGame(text=text)
            elif request_peer is not None:
                if isinstance(request_peer, dict):
                    btn = KeyboardButtonRequestPeer(text=text, **request_peer)
                else:
                    btn = KeyboardButtonRequestPeer(
                        text=text,
                        button_id=request_peer.button_id,
                        peer_type=request_peer.peer_type,
                        max_quantity=getattr(request_peer, 'max_quantity', 1),
                    )
            elif user_profile is not None:
                btn = user_profile if isinstance(user_profile, InputKeyboardButtonUserProfile) else InputKeyboardButtonUserProfile(text, user_profile)
            elif request_phone:
                btn = KeyboardButtonRequestPhone(text=text)
            elif request_location:
                btn = KeyboardButtonRequestGeoLocation(text=text)
            else:
                btn = KeyboardButtonCallback(text=text, data=b'')
        except Exception as e:
            LOGGER.error(f"Failed to create button: {e}")
            raise

        if not position:
            self._button.append(btn)
        elif position == "header":
            self._header_button.append(btn)
        elif position == "footer":
            self._footer_button.append(btn)

    def build_menu(self, b_cols=1, h_cols=8, f_cols=8):
        menu = [self._button[i:i + b_cols] for i in range(0, len(self._button), b_cols)]
        if self._header_button:
            if len(self._header_button) > h_cols:
                for i in range(0, len(self._header_button), h_cols):
                    menu.insert(0, self._header_button[i:i + h_cols])
            else:
                menu.insert(0, self._header_button)
        if self._footer_button:
            if len(self._footer_button) > f_cols:
                for i in range(0, len(self._footer_button), f_cols):
                    menu.append(self._footer_button[i:i + f_cols])
            else:
                menu.append(self._footer_button)
        return ReplyInlineMarkup(rows=[KeyboardButtonRow(buttons=row) for row in menu])

    def reset(self):
        self._button = []
        self._header_button = []
        self._footer_button = []

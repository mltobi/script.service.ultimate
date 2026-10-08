# streaming_providers/providers/_template/catchup_manager.py
"""
{TODO: Provider name} catchup manager (optional).

Include this file only if the provider supports timeshift / restart.
Providers without catchup don't create a catchup manager -- the
provider's implements_catchup is False and calls to
get_catchup_manifest return None.

See ../_template/README.md for the contract.

Reference implementations
-------------------------
MoveTV's provider (providers/movetv/provider.py) implements catchup
by resolving an EPG entry, then POSTing to a catchup-source endpoint
that returns a URL + a play-auth header. The URL and header are
coupled, so the manager needs a reference to the EPG manager (to
resolve epg_id) and to the channel manager (for the channel's stream
uid).

Magenta EU's provider (providers/magentaeu/provider.py) implements
catchup by appending start/end query parameters to the live manifest
URL via build_catchup_url().

simpliTV's catchup only takes a start bound: it passes end_time=None
through and documents that it ignores it. The router parses the
"catchup:<codename>@<ts>" id (an explicit branch above _route) and
hands the parsed arguments to this manager.

HRTi has no catchup -- its VOD and EPG are separate domains, and
authorize_session's session id is not reused for timeshift.

State sharing
-------------
The catchup step often shares state with the channel manager (the live
manifest URL) or the EPG manager (the epg_id for the requested window).
Pass those collaborators as explicit keyword-only arguments rather than
reaching back to the provider (the provider's _build_catchup does this).

Do NOT fall back to the live manifest
-------------------------------------
If get_catchup_manifest cannot resolve catchup for the given window,
return None. Do not return the live manifest URL as a "catchup"
manifest -- the DRM pipeline would extract PSSH from the live stream,
which may differ from the catchup stream's encryption context. Callers
that want the live manifest on failure call provider.get_manifest().

end_time is Optional[int]
-------------------------
If the provider's API takes only a start bound, accept None and document
that it is ignored. If the API needs both bounds, raise BadRequestError
on None. Never pass a sentinel (0, start_time + 1800) when the ABC
accepts None.
"""

from typing import List, Optional

from ...base.managers import CatchupManager
from ...base.models import DRMConfig
from ...base.utils.logger import logger

# from ...base.errors import BadRequestError


class YourCatchupManager(CatchupManager):
    """Catchup for {TODO: provider name}."""

    def __init__(
        self,
        *,
        http_manager,
        auth,
        country,
        config,
        channels=None,
        epg=None,
    ):
        super().__init__(
            http_manager=http_manager,
            auth=auth,
            country=country,
            config=config,
        )
        # Common collaborators. Catchup often needs one or both.
        #   - channels: for resolving a channel's live manifest URL
        #     (Magenta, simpliTV) or its stream uid (MoveTV).
        #   - epg: for resolving an epg_id from a start_time
        #     (MoveTV).
        self._channels = channels
        self._epg = epg

    # ----- Capability -----

    @property
    def catchup_window_hours(self) -> int:
        """Return the catchup window in hours. 0 means no catchup."""
        return 0  # TODO: e.g. 168 for 7 days

    # ----- Abstract method -----

    def get_catchup_manifest(
        self,
        content_id: str,
        start_time: int,
        end_time: Optional[int] = None,
        epg_id: Optional[str] = None,
        **kw,
    ) -> Optional[str]:
        """
        Return the catchup manifest URL, or None if not resolvable.

        start_time / end_time are integer epoch seconds. end_time may be
        None (see module docstring).

        Do NOT fall back to the live manifest URL here.
        """
        raise NotImplementedError("YourCatchupManager.get_catchup_manifest")

    # ----- Concrete methods (override when needed) -----

    # def get_catchup_drm(
    #     self,
    #     content_id: str,
    #     start_time: int,
    #     end_time: Optional[int] = None,
    #     epg_id: Optional[str] = None,
    #     **kw,
    # ) -> List[DRMConfig]:
    #     """
    #     Override only if catchup needs DRM configs. The base implementation
    #     raises NotImplementedError and the DRM pipeline then extracts PSSH from
    #     the catchup manifest itself (it does NOT silently reuse live DRM).
    #     If catchup uses exactly the same licence as live (e.g. a DVR sliding
    #     window on the live stream), implement it explicitly as:
    #         return self.get_drm(content_id, content_type=CONTENT_TYPE_LIVE)
    #     Encrypted channels whose catchup manifest carries no PSSH/default_KID
    #     REQUIRE this — otherwise licensing fails with an empty DRM config.
    #     """
    #     return self.get_drm(content_id, content_type=CONTENT_TYPE_LIVE)

    # ----- Catchup manifest rewrite (optional) -----
    #
    # If the provider's catchup URL is the live DVR manifest and the backend must
    # rewrite it (e.g. start playback at the programme start, bound a running
    # programme) rather than redirect to the CDN, set this on the PROVIDER class
    # (not the catchup manager) and implement rewrite_catchup_manifest:
    #
    #     @property
    #     def rewrites_catchup_manifest(self) -> bool:
    #         return True
    #
    #     def rewrite_catchup_manifest(self, mpd_content, start_time, end_time):
    #         return YourCatchupAdjuster.adjust_window(mpd_content, start_time, end_time)
    #
    # The stream route then fetches, rewrites, injects an absolute BaseURL and
    # serves the manifest body instead of a 302 redirect. Providers that don't set
    # this (the default) keep the plain redirect behaviour.

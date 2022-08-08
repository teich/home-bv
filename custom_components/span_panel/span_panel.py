"""Module to read production and consumption values from a Span panel on the local network."""
import asyncio
import logging
import time

import httpx

STATUS_URL = "http://{}/api/v1/status"
SPACES_URL = "http://{}/api/v1/spaces"
PANEL_URL = "http://{}/api/v1/panel"

_LOGGER = logging.getLogger(__name__)


SPAN_SPACES = "spaces"
SPAN_SYSTEM = "system"
SYSTEM_DOOR_STATE = "doorState"
SYSTEM_DOOR_STATE_CLOSED = "CLOSED"
SYSTEM_DOOR_STATE_OPEN = "OPEN"
SYSTEM_ETHERNET_LINK = "eth0Link"
SYSTEM_CELLULAR_LINK = "wwanLink"
SYSTEM_WIFI_LINK = "wlanLink"

class SpanPanel:
    """Instance of a Span panel"""

    def __init__(
        self,
        host,
        async_client=None,
    ):
        """Init the SPAN."""
        self.host = host.lower()
        self.serial_number = None
        self.status_results = None
        self.spaces = SpanPanelSpaces(self)
        self.panel_results = None
        self._async_client = async_client

    @property
    def async_client(self):
        """Return the httpx client."""
        return self._async_client or httpx.AsyncClient(verify=False)

    async def _async_fetch_with_retry(self, url, **kwargs):
        """Retry 3 times to fetch the url if there is a transport error."""
        for attempt in range(3):
            _LOGGER.debug(
                "HTTP GET Attempt #%s: %s",
                attempt + 1,
                url,
            )
            try:
                async with self.async_client as client:
                    resp = await client.get(url, timeout=30, **kwargs
                    )
                    _LOGGER.debug("Fetched from %s: %s: %s", url, resp, resp.text)
                    return resp
            except httpx.TransportError:
                if attempt == 2:
                    raise

    async def _async_post(self, url, json=None, **kwargs):
        _LOGGER.debug("HTTP POST Attempt: %s", url)
        try:
            async with self.async_client as client:
                resp = await client.post(url, json=json, timeout=30, **kwargs)
                _LOGGER.debug("HTTP POST %s: %s: %s", url, resp, resp.text)
                return resp
        except httpx.TransportError:  # pylint: disable=try-except-raise
            raise

    async def getData(self, url):
        """Fetch data from the endpoint and if inverters selected default"""
        """to fetching inverter data."""
        """Update from PC endpoint."""
        formatted_url = url.format(self.host)
        response = await self._async_fetch_with_retry(
            formatted_url, follow_redirects=False
        )
        return response

    async def setJSONData(self, url, id, json):
        """Fetch data from the endpoint and if inverters selected default"""
        """to fetching inverter data."""
        """Update from PC endpoint."""
        formatted_url = url.format(self.host, id)
        response = await self._async_post(formatted_url, json)
        return response

    async def getPanelData(self):
        self.panel_results = await self.getData(PANEL_URL)

        return

    async def getStatusData(self):
        self.status_results = await self.getData(STATUS_URL)

        if self.serial_number == None:
           raw_json = self.status_results.json()
           self.serial_number = raw_json[SPAN_SYSTEM]["serial"]

        return

    def is_door_closed(self):
        """Running getData() beforehand will set self.enpoint_type and"""
        """self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        raw_json = self.status_results.json()
        doorState = raw_json[SPAN_SYSTEM][SYSTEM_DOOR_STATE]
        if doorState == SYSTEM_DOOR_STATE_CLOSED:
           return True
        else:
           return False

    def is_door_open(self):
        return not self.is_door_closed()

    def is_ethernet_connected(self):
        raw_json = self.status_results.json()
        return raw_json['network'][SYSTEM_ETHERNET_LINK]

    def is_wifi_connected(self):
        raw_json = self.status_results.json()
        return raw_json['network'][SYSTEM_WIFI_LINK]

    def is_cellular_connected(self):
        raw_json = self.status_results.json()
        return raw_json['network'][SYSTEM_CELLULAR_LINK]

    def firmware_version(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        raw_json = self.status_results.json()
        return raw_json["software"]["firmwareVersion"]

    def model(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        raw_json = self.status_results.json()
        return raw_json["system"]["model"]

    def run_in_console(self):
        """If running this module directly, print all the values in the console."""
        print("Reading...")
        loop = asyncio.get_event_loop()
        data_results = loop.run_until_complete(
            asyncio.gather(self.spaces.getData(), self.getStatusData(), self.getPanelData(), return_exceptions=False)
        )

        print("SN: %s" % self.serial_number)
        print("FW: %s" % self.firmware_version())
        print("Model: %s" % self.model())
        print("Door Open: %s" % self.is_door_open())
        print("Door Closed: %s" % self.is_door_closed())
        print("ETH link: %s" % self.is_ethernet_connected())
        print("WiFi link: %s" % self.is_wifi_connected())
        print("Cell link: %s" % self.is_cellular_connected())

        for k in self.spaces.keys():
           print(self.spaces.name(k))
           print("===================")
           print("id: %s" % k)
           print("power: %sW" % self.spaces.power(k))
           print("produced: %sWh" % self.spaces.energy_produced(k))
           print("consumed: %sWh" % self.spaces.energy_consumed(k))
           print("relay open: %s" % self.spaces.is_relay_open(k))
           print("relay closed: %s" % self.spaces.is_relay_closed(k))
           print("prio: %s" % self.spaces.get_priority(k))
           print("user: %s" % self.spaces.is_user_controllable(k))
           print(self.spaces.breaker_positions(k))
           print("")

#        data_results = loop.run_until_complete(
#            asyncio.gather(self.spaces.set_priority('7ef7a4091cdd4910a582b35b40768598', 'NOT_ESSENTIAL'))
#        )

        data_results = loop.run_until_complete(
            asyncio.gather(self.spaces.set_relay_closed('7ef7a4091cdd4910a582b35b40768598'))
        )

        while True:
          loop = asyncio.get_event_loop()
          results = loop.run_until_complete(
             asyncio.gather(
                  self.spaces.getData(),
                  self.getPanelData(),
                  self.getStatusData(),
                  return_exceptions=False,
             )
          )

#          print("results %s" % results)

          time.sleep(10)

SPACES_NAME = "name"
SPACES_RELAY = "relayState"
SPACES_RELAY_OPEN = "OPEN"
SPACES_RELAY_CLOSED = "CLOSED"
SPACES_POWER = "instantPowerW"
SPACES_ENERGY_PRODUCED = "importEnergyAccumWh"
SPACES_ENERGY_CONSUMED = "exportEnergyAccumWh"
SPACES_BREAKER_POSITIONS = "tabs"
SPACES_PRIORITY = "priority"
SPACES_IS_USER_CONTROLLABLE = "is_user_controllable"
SPACES_IS_SHEDDABLE = "is_sheddable"
SPACES_IS_NEVER_BACKUP = "is_never_backup"

class SpanPanelSpaces:
    """Instance of a Span panel"""
    def __init__(
        self,
        panel: SpanPanel,
    ):
        """Init the SPAN."""
        self.panel = panel
        self.json_data = None

    async def getData(self):
        """Fetch data from the endpoint and if inverters selected default"""
        """to fetching inverter data."""
        """Update from PC endpoint."""

        results = await self.panel.getData(SPACES_URL)

        # Can get:
        # HTTPStatusError - httpx.HTTPStatusError: Server error '500 Internal Server Error' for url 'http://span.lan/api/v1/spaces'
        results.raise_for_status()

        self.json_data = results.json()[SPAN_SPACES]

        return

    def keys(self):
        return self.json_data.keys()

    def name(self, id):
        return self.json_data[id][SPACES_NAME]

    def power(self, id):
        return self.json_data[id][SPACES_POWER]

    def energy_produced(self, id):
        return self.json_data[id][SPACES_ENERGY_PRODUCED]

    def energy_consumed(self, id):
        return self.json_data[id][SPACES_ENERGY_CONSUMED]

    def is_relay_open(self, id):
        relayState = self.json_data[id][SPACES_RELAY]
        if relayState == SPACES_RELAY_CLOSED:
           return False
        else:
           return True

    def is_relay_closed(self, id):
        return not self.is_relay_open(id)

    async def _set_relay(self, id, state):
        # state should be "OPEN" or "CLOSED"
        json = {"relay_state_in":{"relayState":state}}
        results = await self.panel.setJSONData(SPACES_URL+"/{}", id, json)

    async def set_relay_closed(self, id):
        await self._set_relay(id, SPACES_RELAY_CLOSED)

    async def set_relay_open(self, id):
        await self._set_relay(id, SPACES_RELAY_OPEN)

    def breaker_positions(self, id):
        return self.json_data[id][SPACES_BREAKER_POSITIONS]

    def get_priority(self, id):
        # should be 'NOT_ESSENTIAL', 'MUST_HAVE', or 'NICE_TO_HAVE'
        return self.json_data[id][SPACES_PRIORITY]

    async def set_priority(self, id, priority):
        json = {"priority_in":{"priority":priority}}
        results = await self.panel.setJSONData(SPACES_URL+"/{}", id, json)

        # add error checking code on response, we can get:
        # '<Response [400 Bad Request]>' if 'id' has 'is_user_controllable'
        # set to False

    def is_user_controllable(self, id):
        return self.json_data[id][SPACES_IS_USER_CONTROLLABLE]



if __name__ == "__main__":
    HOST = "span.lan"

    TESTSPAN = SpanPanel(HOST)

    TESTSPAN.run_in_console()

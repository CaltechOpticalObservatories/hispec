import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
import sys

@dataclass
class EDS0065DATA:
    rom_id: str = None
    health: int = None
    channel: int = None
    raw_data: str = None
    relative_humidity: float = None
    temperature: float = None
    humidity: float = None
    dew_point: float = None
    humidex: float = None
    heat_index: float = None
    version: float = None
    
@dataclass
class EDS0068DATA:
    rom_id: str = None
    health: int = None
    channel: int = None
    raw_data: str = None
    relative_humidity: float = None
    temperature: float = None
    humidity: float = None
    dew_point: float = None
    humidex: float = None
    heat_index: float = None
    pressure_mb: float = None
    pressure_hg: float = None
    illuminance: int = None
    version: float = None

@dataclass
class ONEWIREDATA:
    poll_count: int = None
    total_devices: int = None
    loop_time: float = None
    ch1_connected: int = None
    ch2_connected: int = None
    ch3_connected: int = None
    ch1_error: int = None
    ch2_error: int = None
    ch3_error: int = None
    ch1_voltage: float = None
    ch2_voltage: float = None
    ch3_voltage: float = None
    voltage_power: float = None
    device_name: str = None
    hostname: str = None
    mac_address: str = None
    datetime: str = None
    eds0065_data: list[EDS0065DATA] = field(default_factory=list)
    eds0068_data: list[EDS0068DATA] = field(default_factory=list)

class ONEWIRE:
    def __init__(self, address, timeout=1):
        self.address = address
        self.http_port = 80
        self.udp_port = 30303
        self.tcp_port = 15145
        self.timeout = timeout
        
        self.ow_data = ONEWIREDATA()
        
    async def __aenter__(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.address, self.http_port)
            # if self.logger:
            #     self.logger.info(f"Connected to {self.address}:{self.port}")
        except ConnectionRefusedError as err:
            # if self.logger:
            #     self.logger.error(f"Connection refused: {err}")
            raise DeviceConnectionError("Could not connect to {}".format(self.address)) from err
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            # if self.logger:
            #     self.logger.info("Connection closed")

    async def get_xml_data(self):
        query = ("GET /details.xml HTTP/1.1\r\n\r\n")
        self.writer.write(query.encode("ascii"))
        self.writer.drain

        http_response = await self.reader.readuntil(b'\r\n')
        try:
            self.__http_response_handler(http_response)
        except HttpResponseError as err:
            print(err)
            sys.exit(1)

        while True:
            next_response = await self.reader.readuntil(b'\r\n')
            next_response = next_response.decode("ascii")
            next_response = next_response.split(' ')[0]
            if next_response == "<?xml":
                break
        
        xml_data = await self.reader.readuntil(b'</Devices-Detail-Response>\r\n')
        self.__xml_data_handler(xml_data)

        return xml_data
    
    def __http_response_handler(self, response):
        response = response.decode("ascii")
        response_code = int(response.split(' ')[1])

        if response_code == 404:
            raise HttpResponseError("Http response error: {}".format(response_code))
        elif response_code == 200:
            return
        
    def __xml_data_handler(self, xml_data):
        root = ET.fromstring(xml_data)
        # ET.register_namespace("", "http://www.embeddeddatasystems.com/schema/owserver")
        for elem in root.iter():
            tag_elements = elem.tag.split("}")
            elem.tag = tag_elements[1]
            
        # ET.dump(root)
        # for elem in root.iter():
        #     print(elem.tag, elem.attrib, elem.text)
        
        for elem in root.iter():
            self.__device_data_handler(elem)
                
    def __device_data_handler(self, element):
        if element.tag == "PollCount":
            self.ow_data.poll_count = int(element.text)
        elif element.tag == "DevicesConnected":
            self.ow_data.total_devices = int(element.text)
        elif element.tag == "LoopTime":
            self.ow_data.loop_time = float(element.text)
        elif element.tag == "DevicesConnectedChannel1":
            self.ow_data.ch1_connected = int(element.text)
        elif element.tag == "DevicesConnectedChannel2":
            self.ow_data.ch2_connected = int(element.text)
        elif element.tag == "DevicesConnectedChannel3":
            self.ow_data.ch3_connected = int(element.text)
        elif element.tag == "DataErrorsChannel1":
            self.ow_data.ch1_error = int(element.text)
        elif element.tag == "DataErrorsChannel2":
            self.ow_data.ch2_error = int(element.text)
        elif element.tag == "DataErrorsChannel3":
            self.ow_data.ch3_error = int(element.text)
        elif element.tag == "VoltageChannel1":
            self.ow_data.ch1_voltage = float(element.text)
        elif element.tag == "VoltageChannel2":
            self.ow_data.ch2_voltage = float(element.text)
        elif element.tag == "VoltageChannel3":
            self.ow_data.ch3_voltage = float(element.text)
        elif element.tag == "VoltagePower":
            self.ow_data.voltage_power = float(element.text)
        elif element.tag == "DeviceName":
            self.ow_data.device_name = str(element.text)
        elif element.tag == "HostName":
            self.ow_data.hostname = str(element.text)
        elif element.tag == "MACAddress":
            self.ow_data.mac_address = str(element.text)
        elif element.tag == "DateTime":
            self.ow_data.datetime = str(element.text)
        elif element.tag == "owd_EDS0065":
            self.__sensor_data_handler(element, sensor_type="EDS0065")
        elif element.tag == "owd_EDS0068":
            self.__sensor_data_handler(element, sensor_type="EDS0068")
            
    def __sensor_data_handler(self, element, sensor_type):
        if sensor_type == "EDS0065":
            eds0065_data = EDS0065DATA()
            for sensor in element:
                # print(sensor.tag, sensor.attrib, sensor.text)
                if sensor.tag == "ROMId":
                    eds0065_data.rom_id = str(sensor.text)
                elif sensor.tag == "Health":
                    eds0065_data.health = int(sensor.text)
                elif sensor.tag == "Channel":
                    eds0065_data.channel = int(sensor.text)
                elif sensor.tag == "RawData":
                    eds0065_data.raw_data = str(sensor.text)
                elif sensor.tag == "PrimaryValue":
                    data = sensor.text.split(" ")[0]
                    eds0065_data.relative_humidity = float(data)
                elif sensor.tag == "Temperature":
                    eds0065_data.temperature = float(sensor.text)
                elif sensor.tag == "Humidity":
                    eds0065_data.humidity = float(sensor.text)
                elif sensor.tag == "DewPoint":
                    eds0065_data.dew_point = float(sensor.text)
                elif sensor.tag == "Humidex":
                    eds0065_data.humidex = float(sensor.text)
                elif sensor.tag == "HeatIndex":
                    eds0065_data.heat_index = float(sensor.text)
                elif sensor.tag == "Version":
                    eds0065_data.version = float(sensor.text)
                    
            self.ow_data.eds0065_data.append(eds0065_data)
        elif sensor_type == "EDS0068":
            eds0068_data = EDS0068DATA()
            for sensor in element:
                # print(sensor.tag, sensor.attrib, sensor.text)
                if sensor.tag == "ROMId":
                    eds0068_data.rom_id = str(sensor.text)
                elif sensor.tag == "Health":
                    eds0068_data.health = int(sensor.text)
                elif sensor.tag == "Channel":
                    eds0068_data.channel = int(sensor.text)
                elif sensor.tag == "RawData":
                    eds0068_data.raw_data = str(sensor.text)
                elif sensor.tag == "PrimaryValue":
                    data = sensor.text.split(" ")[0]
                    eds0068_data.relative_humidity = float(data)
                elif sensor.tag == "Temperature":
                    eds0068_data.temperature = float(sensor.text)
                elif sensor.tag == "Humidity":
                    eds0068_data.humidity = float(sensor.text)
                elif sensor.tag == "DewPoint":
                    eds0068_data.dew_point = float(sensor.text)
                elif sensor.tag == "Humidex":
                    eds0068_data.humidex = float(sensor.text)
                elif sensor.tag == "HeatIndex":
                    eds0068_data.heat_index = float(sensor.text)
                elif sensor.tag == "BarometricPressureMb":
                    eds0068_data.pressure_mb = float(sensor.text)
                elif sensor.tag == "BarometricPressureHg":
                    eds0068_data.pressure_hg = float(sensor.text)
                elif sensor.tag == "Light":
                    eds0068_data.illuminance = int(sensor.text)
                elif sensor.tag == "Version":
                    eds0068_data.version = float(sensor.text)
            self.ow_data.eds0068_data.append(eds0068_data)

class HttpResponseError(Exception):
    pass

class DeviceConnectionError(Exception):
    pass

async def test_onewire(ow_address) -> ONEWIREDATA:
    async with ONEWIRE(ow_address) as ow:
        await ow.get_xml_data()
        
    return ow.ow_data
        
if __name__ == "__main__":
    OW_ADDRESS = ""
    ow_data = asyncio.run(test_onewire(OW_ADDRESS))
    print(ow_data)

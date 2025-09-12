"""
WASAPI Device Discovery and Selection
Enumerates audio devices and auto-selects mic + loopback
"""

import sounddevice as sd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
try:
    from .config import config
except ImportError:
    from config import config


@dataclass
class AudioDevice:
    id: int
    name: str
    channels: int
    is_input: bool
    is_loopback: bool
    hostapi: str
    
    
class DeviceManager:
    """Manages WASAPI device discovery and selection"""
    
    def __init__(self):
        self._devices_cache = None
        
    def enumerate_devices(self) -> List[AudioDevice]:
        """Enumerate all audio devices with WASAPI loopback detection"""
        devices = []
        
        try:
            # Get device list from sounddevice
            device_list = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            for i, device in enumerate(device_list):
                if device is None:
                    continue
                    
                hostapi = hostapis[device['hostapi']]
                is_wasapi = 'WASAPI' in hostapi['name']
                
                # Detect loopback devices (WASAPI render devices with input channels)
                is_loopback = (is_wasapi and 
                             device['max_input_channels'] > 0 and 
                             device['max_output_channels'] > 0 and
                             'loopback' in device['name'].lower())
                
                devices.append(AudioDevice(
                    id=i,
                    name=device['name'],
                    channels=max(device['max_input_channels'], device['max_output_channels']),
                    is_input=device['max_input_channels'] > 0,
                    is_loopback=is_loopback,
                    hostapi=hostapi['name']
                ))
        
        except Exception as e:
            print(f"Error enumerating devices: {e}")
            
        self._devices_cache = devices
        return devices
    
    def get_devices(self) -> List[AudioDevice]:
        """Get cached device list or enumerate if not cached"""
        if self._devices_cache is None:
            return self.enumerate_devices()
        return self._devices_cache
    
    def auto_select_devices(self) -> Tuple[Optional[AudioDevice], Optional[AudioDevice]]:
        """Auto-select mic (first input) and loopback (first render loopback)"""
        devices = self.get_devices()
        
        mic_device = None
        loopback_device = None
        
        # Apply preferred device overrides from config
        if config.preferred_devices.mic is not None:
            try:
                mic_device = next(d for d in devices if d.id == config.preferred_devices.mic)
            except StopIteration:
                print(f"Warning: Preferred mic device {config.preferred_devices.mic} not found")
        
        if config.preferred_devices.loopback is not None:
            try:
                loopback_device = next(d for d in devices if d.id == config.preferred_devices.loopback)
            except StopIteration:
                print(f"Warning: Preferred loopback device {config.preferred_devices.loopback} not found")
        
        # Auto-select if not overridden
        if mic_device is None:
            # Find first input device (exclude loopbacks)
            for device in devices:
                if device.is_input and not device.is_loopback and device.channels > 0:
                    mic_device = device
                    break
        
        if loopback_device is None:
            # Find first loopback device  
            for device in devices:
                if device.is_loopback:
                    loopback_device = device
                    break
        
        return mic_device, loopback_device
    
    def validate_device_selection(self, mic_device: AudioDevice, loopback_device: AudioDevice) -> Dict[str, bool]:
        """Validate selected devices are usable"""
        validation = {
            "mic_available": False,
            "loopback_available": False,
            "sample_rate_supported": False
        }
        
        try:
            # Test mic device
            if mic_device:
                sd.check_input_settings(device=mic_device.id, 
                                      channels=1, 
                                      samplerate=config.audio.sample_rate)
                validation["mic_available"] = True
        except Exception as e:
            print(f"Mic device {mic_device.id if mic_device else 'None'} validation failed: {e}")
        
        try:
            # Test loopback device  
            if loopback_device:
                sd.check_input_settings(device=loopback_device.id,
                                      channels=1,
                                      samplerate=config.audio.sample_rate)
                validation["loopback_available"] = True
        except Exception as e:
            print(f"Loopback device {loopback_device.id if loopback_device else 'None'} validation failed: {e}")
        
        validation["sample_rate_supported"] = validation["mic_available"] or validation["loopback_available"]
        
        return validation
    
    def get_device_info(self, device_id: int) -> Optional[Dict]:
        """Get detailed device information"""
        try:
            return sd.query_devices(device_id)
        except Exception:
            return None
    
    def list_devices_json(self) -> Dict:
        """Return device list in JSON format with WASAPI host API details"""
        devices = self.get_devices()
        mic_device, loopback_device = self.auto_select_devices()
        
        # Get host API information
        try:
            hostapis = sd.query_hostapis()
            hostapi_info = [
                {
                    "id": i,
                    "name": api['name'],
                    "device_count": api['device_count'],
                    "default_input": api.get('default_input_device', -1),
                    "default_output": api.get('default_output_device', -1)
                }
                for i, api in enumerate(hostapis)
            ]
        except Exception:
            hostapi_info = []
        
        # Filter WASAPI devices
        wasapi_devices = [d for d in devices if 'WASAPI' in d.hostapi]
        wasapi_inputs = [d for d in wasapi_devices if d.is_input and not d.is_loopback]
        wasapi_loopbacks = [d for d in wasapi_devices if d.is_loopback]
        
        return {
            "hostAPIs": hostapi_info,
            "all_devices": [
                {
                    "id": d.id,
                    "name": d.name, 
                    "max_input_channels": d.channels if d.is_input else 0,
                    "max_output_channels": d.channels if not d.is_input else 0,
                    "is_input": d.is_input,
                    "is_loopback": d.is_loopback,
                    "hostapi": d.hostapi
                }
                for d in devices
            ],
            "wasapi_devices": {
                "inputs": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "max_input_channels": d.channels
                    }
                    for d in wasapi_inputs
                ],
                "loopbacks": [
                    {
                        "id": d.id, 
                        "name": d.name,
                        "max_input_channels": d.channels
                    }
                    for d in wasapi_loopbacks
                ]
            },
            "chosenIndices": {
                "mic": mic_device.id if mic_device else None,
                "loopback": loopback_device.id if loopback_device else None
            },
            "validation": self.validate_device_selection(mic_device, loopback_device) if mic_device and loopback_device else {}
        }


# Global device manager instance
device_manager = DeviceManager()
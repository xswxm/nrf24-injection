A tool set for sniffing devices and launching attacks with Crazyradio.
Based on [BastilleResearch](https://github.com/BastilleResearch/nrf-research-firmware.git "nrf-research-firmware")'s research.

### Setting Up
Install additional modules
```sh
sudo apt-get install sdcc binutils python python-pip
sudo pip install -U pip
sudo pip install -U -I pyusb
sudo pip install -U platformio
```

### Supported Devices
| Device  | Sniff | Attack | Details |
| ----------------- | ----------------- | ----------------- | ----------------- |
| AmazonBasics | Yes(unresponsive) | Yes | Mice control and HID Injection |
| Logitech Mice | Yes | Yes | Mice control |


### How to Use
```sh
sudo python app.py
```

### How to Use Launch Attacks
```sh
# Please check attacking rules in 'devices/*.py' for details
# Further infomation will added to here once I have time
# Attacking thread sleeps for 100 milliseconds
<SLP(100)>
# Move mouse by 100*100 and press Left, Right and Middle buttons
<MOV(100,100,LMR)>
# Release the buttons for mice, you can send another MOV command without any buttons
<MOV(0,0)>
<MOV()>
# Send keystrokes to release all keys
<RLS>
# Send 'Windows + r' key combination
<WIN+r>
# Send 'Ctrl + Alt + Delete' key combination
<CTRL+ALT+DEL>
# Open Powershell and then open Caculator form powershell with Windows computers
<RLS><WIN+r><RLS><SLP(500)><RLS>powershell<ENTER><RLS><SLP(500)><RLS>calc<ENTER><RLS>
```

License
----
GPL

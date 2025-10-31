# AquaBle

*pronounced* "AK-wuh-bul" (/ˈækwə//bəl/)

**Current project state: in very active development, at a very early stage.** *Expect further functionality and refinement soon.*

Maintained by **Caleb Venner**. This project builds on the open-source work published as [Chihiros LED Control](https://github.com/TheMicDiet/chihiros-led-control) by Michael Dietrich. The original project is licensed under MIT; all redistributions of this codebase continue to honour that license and retain the upstream attribution.

### Legal Disclaimer

**This project is not affiliated with, endorsed by, or approved by Chihiros Aquatic Studio or Shanghai Ogino Biotechnology Co.,Ltd.** This is an independent, open-source software project developed through reverse engineering and community contributions.

- We do not reproduce, distribute, or claim ownership of any proprietary Chihiros software code
- Device compatibility is based on publicly available Bluetooth Low Energy protocol analysis
- Use of this software with Chihiros devices is at your own risk
- "Chihiros" is a trademark of Chihiros Aquatic Studio (Shanghai Ogino Biotechnology Co.,Ltd) and is used here solely for device identification purposes
- This software is provided "as-is" without warranty of any kind

## Installation

AquaBle is distributed as a Home Assistant add-on with Ingress support for seamless access.

1. Add the custom repository: `https://github.com/caleb-venner/aquable`
2. Install the "AquaBle" add-on from the repository
3. Start the add-on
4. Click **"OPEN WEB UI"** in the add-on info screen

The web interface is accessible through Home Assistant Ingress, providing seamless integration with no port forwarding or authentication configuration needed.

### Home Assistant Ingress

AquaBle is designed exclusively for Home Assistant Ingress:

- Access the web interface directly through the Home Assistant UI
- No port forwarding or authentication configuration needed
- Seamless user experience within Home Assistant
- Works perfectly on Home Assistant mobile apps

For technical details, see [INGRESS.md](aquable/INGRESS.md).

## Supported Devices

- Chihiros LED Aquarium Lights
- Chihiros Dosing Pumps

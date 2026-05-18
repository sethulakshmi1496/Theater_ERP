"""Operations service helpers"""


def send_lamp_alert(screen):
    """Alert MD when lamp balance < threshold."""
    print(f"[ALERT] {screen.name}: Lamp balance critically low at {screen.lamp_balance} hrs!")

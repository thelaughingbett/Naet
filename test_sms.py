# test_sms.py
import requests

MESSAGEPIT_URL = 'http://localhost:8200'


def send_test_sms(to, body, from_number='+15550000000'):
    print(f"\nSending SMS...")
    print(f"  From : {from_number}")
    print(f"  To   : {to}")
    print(f"  Body : {body}")

    try:
        response = requests.post(
            f"{MESSAGEPIT_URL}/2010-04-01/Accounts/test/Messages.json",
            data={
                'From': from_number,
                'To': to,
                'Body': body,
            },
            auth=('test', 'test'),
        )
        response.raise_for_status()
        data = response.json()
        print(f"\n✓ SMS captured by MessagePit!")
        print(f"  SID    : {data.get('sid')}")
        print(f"  Status : {data.get('status')}")
        print(f"\n→ View it at http://localhost:8025")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to MessagePit.")
        print("  Make sure messagepit.exe is running.")
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Error: {e}")
        print(f"  Response: {response.text}")


if __name__ == '__main__':
    send_test_sms(
        to='+254712345678',
        body='Hello! Your OTP is 948321',
    )

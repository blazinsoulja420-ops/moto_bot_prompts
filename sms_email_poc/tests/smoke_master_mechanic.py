from sms_email_poc.master_mechanic import generate_report


def main():
    sample = generate_report("P0420", obd_data={"RPM": 900})
    print(sample)


if __name__ == "__main__":
    main()

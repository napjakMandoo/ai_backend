import time
import schedule

if __name__ == "__main__":
    schedule.every().day.at("21:12").do(print, "hello")

    while True:
        schedule.run_pending()
        time.sleep(1)
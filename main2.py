import cv2
import os
import sqlite3
from datetime import datetime
import time

DB_PATH    = "qrcodes.db"
OUTPUT_DIR = "captured_frames"
CAM_INDEX  = 1  # change if your OBS virtual cam is at a different index

def init_db(path):
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qrcodes (
        data TEXT PRIMARY KEY,
        first_seen TIMESTAMP
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS duplicates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        seen_at TIMESTAMP
    )""")
    conn.commit()
    return conn

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = init_db(DB_PATH)
    cur  = conn.cursor()

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print(f"Cannot open camera {CAM_INDEX}")
        return
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = cv2.QRCodeDetector()
    seen = set()

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        try:
            data, bbox, _ = detector.detectAndDecode(frame)
        except:
            continue
        else:
            if bbox is not None and data:
                now = datetime.now()
                ts  = now.strftime("%Y-%m-%d %H:%M:%S")

                # draw bounding box on the frame
                pts = bbox.astype(int).reshape(-1, 2)
                for i in range(len(pts)):
                    cv2.line(frame, tuple(pts[i]),
                            tuple(pts[(i+1) % len(pts)]),
                            (0,255,0), 2)

                if data not in seen:
                    seen.add(data)

                    # save full frame instead of just the QR crop
                    fname = now.strftime("%Y%m%d_%H%M%S") + ".jpg"
                    path  = os.path.join(OUTPUT_DIR, fname)
                    cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                    print(f"[NEW]       {data!r} → saved full frame {fname}")

                    cur.execute(
                        "INSERT OR IGNORE INTO qrcodes(data, first_seen) VALUES (?,?)",
                        (data, ts))
                    conn.commit()
                else:
                    pass
                    #print(f"[DUPLICATE] {data!r} at {ts}")
                    #cur.execute(
                    #    "INSERT INTO duplicates(data, seen_at) VALUES (?,?)",
                    #    (data, ts))
                    #conn.commit()

        cv2.imshow("Webcam (q to quit)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()

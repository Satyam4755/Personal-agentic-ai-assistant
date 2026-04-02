import os
import threading
from multiprocessing import Event, Process, Queue
from queue import Empty

ANALYZE_EVERY_N_FRAMES = 20
WINDOW_NAME = "Jarvis Vision"

_active_lock = threading.Lock()
_active_process = None
_active_queue = None
_active_stop_event = None


def _image_path():
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, "scanned.jpg")


def _set_active(process=None, result_queue=None, stop_event=None):
    global _active_process, _active_queue, _active_stop_event

    with _active_lock:
        if process is not None:
            _active_process = process
        if result_queue is not None:
            _active_queue = result_queue
        if stop_event is not None:
            _active_stop_event = stop_event


def _take_active():
    global _active_process, _active_queue, _active_stop_event

    with _active_lock:
        refs = (_active_process, _active_queue, _active_stop_event)
        _active_process = None
        _active_queue = None
        _active_stop_event = None

    return refs


def _release_resources(process, result_queue):
    if process is not None:
        try:
            if process.exitcode is not None:
                process.close()
        except Exception:
            pass

    if result_queue is not None:
        try:
            result_queue.close()
        except Exception:
            pass
        try:
            result_queue.join_thread()
        except Exception:
            pass


def _camera_backend(cv2):
    return getattr(cv2, "CAP_AVFOUNDATION", 0)


def live_scan_process(result_queue, stop_event):
    cap = None

    try:
        import cv2
        from PIL import Image
        from transformers import pipeline

        vision_model = pipeline(
            "image-to-text",
            model="Salesforce/blip-image-captioning-base",
        )

        backend = _camera_backend(cv2)
        for device_index in (0, 1):
            current_cap = cv2.VideoCapture(device_index, backend)
            if current_cap.isOpened():
                cap = current_cap
                break
            current_cap.release()

        if cap is None or not cap.isOpened():
            result_queue.put(("error", "Camera not accessible", None))
            return

        frame_count = 0
        last_label = ""
        image_path = _image_path()

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                continue

            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            frame_count += 1
            if frame_count % ANALYZE_EVERY_N_FRAMES != 0:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            result = vision_model(image)
            label = result[0]["generated_text"].strip() if result else ""

            if not label or label == last_label:
                continue

            last_label = label
            cv2.imwrite(image_path, frame)
            result_queue.put(("update", f"I think this is {label}", image_path))
    except Exception as error:
        result_queue.put(("error", str(error), None))
    finally:
        if cap is not None:
            cap.release()
        try:
            import cv2
            cv2.destroyAllWindows()
        except Exception:
            pass


def stop_scan():
    process, result_queue, stop_event = _take_active()

    if stop_event is not None:
        try:
            stop_event.set()
        except Exception:
            pass

    if process is not None:
        try:
            process.join(timeout=0.8)
        except Exception:
            pass
        try:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
        except Exception:
            pass

    _release_resources(process, result_queue)

    try:
        import cv2
        cv2.destroyAllWindows()
    except Exception:
        pass


def start_live_scan(update_callback, finished_callback=None):
    stop_scan()

    result_queue = Queue()
    stop_event = Event()
    process = Process(target=live_scan_process, args=(result_queue, stop_event))
    process.daemon = True
    process.start()
    _set_active(process=process, result_queue=result_queue, stop_event=stop_event)

    def monitor_results():
        try:
            while True:
                try:
                    kind, response, image_path = result_queue.get(timeout=0.3)
                except Empty:
                    if process.is_alive():
                        continue
                    break
                except (EOFError, OSError, ValueError):
                    break

                if kind in {"update", "error"}:
                    update_callback(response, image_path)

                if kind == "error":
                    break
        finally:
            global _active_process, _active_queue, _active_stop_event
            with _active_lock:
                is_current = (
                    _active_process is process
                    and _active_queue is result_queue
                    and _active_stop_event is stop_event
                )
                if is_current:
                    _active_process = None
                    _active_queue = None
                    _active_stop_event = None

            try:
                if process.is_alive():
                    stop_event.set()
                    process.join(timeout=0.5)
            except Exception:
                pass

            _release_resources(process, result_queue)

            try:
                import cv2
                cv2.destroyAllWindows()
            except Exception:
                pass

            if finished_callback is not None:
                finished_callback()

    monitor_thread = threading.Thread(target=monitor_results, daemon=True)
    monitor_thread.start()


def start_scan(callback, finished_callback=None):
    start_live_scan(callback, finished_callback=finished_callback)

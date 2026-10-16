import sys

# (제목, 우선순위, 완료 여부)
TASKS = [
    ("주간 보고서 초안 작성", "HIGH", False),
    ("회의 자료 정리", "MID", False),
    ("책상 정리", "LOW", False),
    ("이메일 답장", "HIGH", True),
]

PRIORITY_ORDER = {"HIGH": 0, "MID": 1, "LOW": 2}


def pending_tasks(tasks):
    return [task for task in tasks if not task[2]]


def sort_by_priority(tasks):
    return sorted(tasks, key=lambda task: PRIORITY_ORDER[task[1]])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tasks = TASKS if "--all" in sys.argv[1:] else pending_tasks(TASKS)
    for title, priority, done in sort_by_priority(tasks):
        suffix = " (완료)" if done else ""
        print(f"[{priority}] {title}{suffix}")


if __name__ == "__main__":
    main()

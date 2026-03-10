"""运行 backtrack target selector v1 的简单演示。"""
from pprint import pprint

from backtrack_target_selector_v1 import (
    BacktrackTargetSelectorV1,
    build_demo_case,
)


def main() -> None:
    selector = BacktrackTargetSelectorV1()
    context, candidates = build_demo_case()
    result = selector.select(context, candidates)

    print("=== Selection Result ===")
    pprint(result.to_dict())


if __name__ == "__main__":
    main()

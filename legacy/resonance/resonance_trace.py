#!/usr/bin/env python3
"""
========================================================
纠缠共振完整迭代追踪
========================================================

展示完整的迭代过程，看循环到底发生在哪里
"""

import numpy as np
from datetime import datetime

class ResonanceTrace:
    def __init__(self):
        self.data_to_parity = {
            0: [1],
            3: [1, 4],
            5: [2, 4],
            6: [2],
        }
        self.parity_to_data = {
            1: [0, 3, 6],
            2: [0, 5, 6],
            4: [3, 5],
        }

        np.random.seed(42)

        print("=" * 60)
        print("  纠缠共振完整迭代追踪")
        print("=" * 60)

    def encode(self, data):
        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]
        code = [0] * 7
        code[0] = D0
        code[3] = D1
        code[5] = D2
        code[6] = D3
        code[1] = D0 ^ D1 ^ D3
        code[2] = D0 ^ D2 ^ D3
        code[4] = D1 ^ D2 ^ D3
        return code

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def get_error_pos(self, syndrome):
        mapping = {1:1, 2:2, 3:0, 4:4, 5:3, 6:5, 7:6}
        return mapping.get(syndrome)

    def get_entangled(self, error_pos):
        entangled = set()
        if error_pos in self.data_to_parity:
            entangled.update(self.data_to_parity[error_pos])
        if error_pos in self.parity_to_data:
            entangled.update(self.parity_to_data[error_pos])
        entangled.discard(error_pos)
        return list(entangled)

    def resonance_flip(self, code, error_pos):
        new_code = code.copy()
        entangled = self.get_entangled(error_pos)
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code, [error_pos] + entangled

    def trace(self, data, error_pos, max_iter=50):
        """完整追踪一次实验"""
        original = self.encode(data)

        print(f"\n原始数据: {data}")
        print(f"原始码:   {original} (校验子: {self.syndrome(original)})")

        current = original.copy()
        current[error_pos] ^= 1

        print(f"错误位:   {error_pos}")
        print(f"错误码:   {current} (校验子: {self.syndrome(current)})")

        print(f"\n迭代过程:")
        history = [(tuple(current), None)]

        for i in range(max_iter):
            syndrome = self.syndrome(current)
            detected_pos = self.get_error_pos(syndrome)
            if detected_pos is None:
                detected_pos = np.random.randint(0, 7)

            after_flip, flipped = self.resonance_flip(current, detected_pos)

            print(f"  步{i+1}: 位置{detected_pos}翻转{flipped} → {after_flip} (syn={self.syndrome(after_flip)})")

            if tuple(after_flip) in [h[0] for h in history]:
                print(f"  → 检测到循环！状态 {after_flip} 之前出现过")
                return i + 1

            current = after_flip
            history.append((tuple(current), flipped))

        print(f"  → 达到最大迭代 {max_iter}")
        return max_iter

    def run(self):
        test_cases = [
            ([0, 1, 1, 0], 4),
            ([1, 0, 1, 1], 2),
            ([0, 0, 1, 1], 5),
        ]

        for data, error_pos in test_cases:
            self.trace(data, error_pos, max_iter=20)


if __name__ == "__main__":
    exp = ResonanceTrace()
    exp.run()
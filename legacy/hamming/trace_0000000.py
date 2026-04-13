#!/usr/bin/env python3
"""
========================================================
追踪0000000的完整轨迹
========================================================
"""

import numpy as np

class Trace0000000:
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
        return new_code

    def trace(self):
        print("追踪 0000000 的完整轨迹")
        print("=" * 60)

        code = [0, 0, 0, 0, 0, 0, 0]
        print(f"起始: {code} (syn={self.syndrome(code)})")

        seen = {tuple(code): 0}
        history = [code]

        for i in range(20):
            syndrome = self.syndrome(code)
            error_pos = self.get_error_pos(syndrome) if syndrome > 0 else None

            print(f"\n步{i}:")
            print(f"  当前: {code} (syn={syndrome})")

            if syndrome == 0:
                print(f"  syndrome=0，不翻转，终止")
                break

            if error_pos is not None:
                print(f"  syndrome={syndrome} → 翻转位置{error_pos}")
            else:
                print(f"  syndrome={syndrome}，无对应位置")

            entangled = self.get_entangled(error_pos or 0)
            print(f"  纠缠位: {entangled}")

            next_code = self.resonance_flip(code, error_pos or 0)
            print(f"  翻转后: {next_code} (syn={self.syndrome(next_code)})")

            key = tuple(next_code)
            if key in seen:
                print(f"  → 状态 {next_code} 已见过（在步{seen[key]}）")
                print(f"  → 检测到循环！")

                # 找出循环部分
                loop_start = seen[key]
                loop_len = i + 1 - loop_start
                print(f"  → 循环长度: {loop_len}")
                print(f"  → 循环部分: {history[loop_start:]} 和 {next_code}")

                # 展示循环部分
                print(f"\n循环部分:")
                for j in range(loop_start, len(history)):
                    print(f"  步{j}: {history[j]}")
                print(f"  步{i+1}: {next_code}")
                print(f"  步{i+2}: {next_code} (回到循环)")

                break

            code = next_code
            seen[key] = i + 1
            history.append(code)


if __name__ == "__main__":
    exp = Trace0000000()
    exp.trace()
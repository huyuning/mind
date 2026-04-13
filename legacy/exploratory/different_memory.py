#!/usr/bin/env python3
"""
========================================================
换一块内存空间：不同的纠缠映射
========================================================

新的纠缠映射（不同的"内存结构"）：
- 位置:     0  1  2  3  4  5  6
- 纠缠:     D0 P0 P1 D1 P2 D2 D3
- 完全图纠缠：每个位置都与所有其他位置纠缠
"""

import numpy as np

class DifferentMemorySpace:
    def __init__(self):
        # 完全图纠缠：每个位置与其他所有位置纠缠
        self.entanglement = {i: [j for j in range(7) if j != i] for i in range(7)}

        print("=" * 60)
        print("  新内存空间：完全图纠缠")
        print("=" * 60)
        print("纠缠映射: 每个位置与其他6个位置纠缠")
        print(f"{self.entanglement}")

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def resonance_flip(self, code, error_pos):
        new_code = code.copy()
        entangled = self.entanglement[error_pos]
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code

    def evolve(self, code, max_iter=1000):
        seen = {tuple(code): 0}
        history = [code]
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos)
            key = tuple(next_code)
            if key in seen:
                return {
                    'loop': True,
                    'loop_len': i + 1 - seen[key],
                    'total_states': len(seen),
                    'history': history,
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop': False, 'total_states': len(seen), 'history': history}

    def run(self):
        print("\n测试所有256种状态...")

        loop_lens = []
        total_states_list = []

        for n in range(256):
            code = [(n >> i) & 1 for i in range(7)]
            result = self.evolve(code)
            loop_lens.append(result['loop_len'])
            total_states_list.append(result['total_states'])

            if (n + 1) % 64 == 0:
                print(f"  进度: {n+1}/256")

        print(f"\n{'='*60}")
        print("  分析结果")
        print(f"{'='*60}")

        print(f"\n循环长度分布:")
        loop_len_counts = {}
        for ll in loop_lens:
            loop_len_counts[ll] = loop_len_counts.get(ll, 0) + 1
        for ll in sorted(loop_len_counts.keys()):
            print(f"  长度{ll}: {loop_len_counts[ll]}次")

        print(f"\n状态数分布:")
        state_counts = {}
        for ts in total_states_list:
            state_counts[ts] = state_counts.get(ts, 0) + 1
        for ts in sorted(state_counts.keys()):
            print(f"  {ts}个状态: {state_counts[ts]}次")

        # 例子
        print(f"\n{'='*60}")
        print("  例子")
        print(f"{'='*60}")

        shown = set()
        for n in range(256):
            code = [(n >> i) & 1 for i in range(7)]
            result = self.evolve(code)
            if result['loop'] and result['loop_len'] not in shown:
                shown.add(result['loop_len'])
                print(f"\n循环长度{result['loop_len']}: {result['history'][:5]}...")

            if len(shown) >= 5:
                break


if __name__ == "__main__":
    exp = DifferentMemorySpace()
    exp.run()
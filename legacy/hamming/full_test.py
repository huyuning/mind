#!/usr/bin/env python3
"""
========================================================
全量测试：0000000 到 1111111 所有256种状态
========================================================

测试：
1. 所有状态是否都能进入稳定循环
2. 稳定循环是否是无限循环
"""

import numpy as np

class FullTest:
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

        print("=" * 60)
        print("  全量测试：256种状态")
        print("=" * 60)

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

    def evolve(self, code, max_iter=1000):
        """演化直到循环或达到最大迭代"""
        seen = {tuple(code): 0}
        history = [code]

        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = self.get_error_pos(syndrome) if syndrome > 0 else i % 7

            next_code = self.resonance_flip(code, error_pos)
            key = tuple(next_code)

            if key in seen:
                loop_start = seen[key]
                loop_len = i + 1 - loop_start
                return {
                    'final': code,
                    'loop': True,
                    'loop_start': loop_start,
                    'loop_len': loop_len,
                    'total_states': len(seen),
                    'iterations': i + 1,
                    'history': history,
                }

            code = next_code
            seen[key] = i + 1
            history.append(code)

        return {
            'final': code,
            'loop': False,
            'total_states': len(seen),
            'iterations': max_iter,
            'history': history,
        }

    def run(self):
        results = []
        loop_lens = []
        total_states_list = []

        print("测试所有256种状态...")

        for n in range(256):
            code = [(n >> i) & 1 for i in range(7)]
            result = self.evolve(code)
            results.append((code, result))

            if result['loop']:
                loop_lens.append(result['loop_len'])
            total_states_list.append(result['total_states'])

            if (n + 1) % 64 == 0:
                print(f"  进度: {n+1}/256")

        # 分析结果
        total = len(results)
        n_loops = sum(1 for _, r in results if r['loop'])
        n_no_loop = total - n_loops

        print(f"\n{'='*60}")
        print("  分析结果")
        print(f"{'='*60}")
        print(f"\n总状态数: {total}")
        print(f"进入循环: {n_loops}/{total} = {n_loops/total*100:.1f}%")
        print(f"未进入循环: {n_no_loop}/{total} = {n_no_loop/total*100:.1f}%")

        if loop_lens:
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

        # 展示各种循环长度的例子
        print(f"\n{'='*60}")
        print("  循环例子")
        print(f"{'='*60}")

        shown_lens = set()
        for code, result in results:
            if result['loop'] and result['loop_len'] not in shown_lens:
                shown_lens.add(result['loop_len'])
                h = result['history']
                print(f"\n起始: {code} → 循环长度{result['loop_len']}")
                print(f"  演变: {' → '.join([str(s) for s in h[:8]])}...")

            if len(shown_lens) >= 5:
                break

        # 检查是否真的是无限循环
        print(f"\n{'='*60}")
        print("  无限循环验证")
        print(f"{'='*60}")

        # 取几个例子继续迭代更多步
        for code, result in results[:5]:
            if result['loop']:
                code = result['final']
                seen = set()
                infinite = True
                for _ in range(10000):
                    syndrome = self.syndrome(code)
                    error_pos = self.get_error_pos(syndrome) if syndrome > 0 else 0
                    code = self.resonance_flip(code, error_pos)
                    key = tuple(code)
                    if key in seen:
                        infinite = False
                        break
                    seen.add(key)

                print(f"起始{result['history'][0]}: {'无限循环' if infinite else '有限终止'}")

        return results


if __name__ == "__main__":
    exp = FullTest()
    results = exp.run()
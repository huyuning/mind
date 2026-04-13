#!/usr/bin/env python3
"""
========================================================
全连接图主线确定性验证
========================================================

同一初始态运行100次，验证是否100%进入同一吸引子
"""

import numpy as np
from datetime import datetime

class DeterminismTest:
    def __init__(self):
        self.graphs = {
            '全连接图主线': {i: [j for j in range(7) if j != i] for i in range(7)},
            '对照-环形': {
                0: [1, 6], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5, 0],
            },
            '对照-星形': {
                0: [1, 2, 3, 4, 5, 6],
                1: [0], 2: [0], 3: [0], 4: [0], 5: [0], 6: [0],
            },
            '对照-链形': {
                0: [1], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5],
            },
        }

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def resonance_flip(self, code, error_pos, entanglement):
        new_code = code.copy()
        entangled = entanglement.get(error_pos, [])
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code

    def evolve(self, code, entanglement, max_iter=10000):
        seen = {tuple(code): 0}
        history = [code]
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                loop_start = seen[key]
                loop_len = i + 1 - loop_start
                cycle_states = tuple(sorted(tuple(s) for s in history[loop_start:]))
                return {
                    'loop': True,
                    'loop_len': loop_len,
                    'cycle_states': cycle_states,
                    'transient_len': loop_start,
                    'final': tuple(code),
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop': False, 'final': tuple(code)}

    def test_determinism(self, name, entanglement, runs=100):
        """同一初始态运行多次"""
        np.random.seed(42)
        initial = [np.random.randint(0, 2) for _ in range(7)]

        print(f"\n  初始态: {initial}")

        cycle_set = set()
        loop_lens = []

        for i in range(runs):
            result = self.evolve(initial, entanglement)
            cycle_set.add(result['cycle_states'])
            loop_lens.append(result['loop_len'])

        unique_attractors = len(cycle_set)
        unique_loop_lens = len(set(loop_lens))

        return {
            'initial': initial,
            'unique_attractors': unique_attractors,
            'unique_loop_lens': unique_loop_lens,
            'runs': runs,
            'deterministic': unique_attractors == 1 and unique_loop_lens == 1,
        }

    def run(self):
        print("=" * 70)
        print("  全连接图主线确定性验证：同一初始态运行100次")
        print("=" * 70)

        results = {}

        for name, entanglement in self.graphs.items():
            print(f"\n【{name}】")
            r = self.test_determinism(name, entanglement)
            results[name] = r

            print(f"  运行次数: {r['runs']}")
            print(f"  唯一吸引子数: {r['unique_attractors']}")
            print(f"  唯一循环长度数: {r['unique_loop_lens']}")
            print(f"  确定性: {'✓ 100%一致' if r['deterministic'] else '✗ 不一致!'}")

        print(f"\n{'='*70}")
        print("  全连接图主线汇总")
        print(f"{'='*70}")
        print(f"\n{'图组':<18} {'唯一吸引子':<15} {'确定性':<15}")
        print("-" * 40)
        for name, r in results.items():
            det = "✓ 100%" if r['deterministic'] else "✗ 不一致"
            print(f"{name:<18} {r['unique_attractors']:<15} {det:<15}")

        print(f"\n结论: 这是{'确定性' if all(r['deterministic'] for r in results.values()) else '非确定性'}动力学系统")


if __name__ == "__main__":
    exp = DeterminismTest()
    exp.run()

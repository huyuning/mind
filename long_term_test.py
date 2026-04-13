#!/usr/bin/env python3
"""
========================================================
全连接图主线长时间稳定性测试
========================================================

不加扰动，每隔1分钟运行一次，共10次
观察每次运行的结果是否一致
"""

import numpy as np
from datetime import datetime

class LongTermStability:
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

        self.runs = 10

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
                return {
                    'loop': True,
                    'loop_len': i + 1 - seen[key],
                    'total_states': len(seen),
                    'final': code,
                    'history': history,
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop': False, 'total_states': len(seen), 'final': code}

    def run_single(self, entanglement, seed):
        """单次运行"""
        np.random.seed(seed)
        code = [np.random.randint(0, 2) for _ in range(7)]
        return self.evolve(code, entanglement)

    def test_long_term(self, name, entanglement):
        """每分钟运行一次，共10次"""
        print(f"\n  【{name}】")
        print(f"  {'次数':<6} {'时间':<12} {'最终态':<15} {'循环长度':<10} {'状态数':<8}")
        print(f"  {'-'*55}")

        results = []
        base_seed = int(datetime.now().timestamp())

        for i in range(self.runs):
            seed = base_seed + i
            result = self.run_single(entanglement, seed)

            results.append({
                'run': i + 1,
                'final': result['final'],
                'loop_len': result['loop_len'],
                'total_states': result['total_states'],
            })

            print(f"  {i+1:<6} {datetime.now().strftime('%H:%M:%S'):<12} {str(result['final']):<15} {result['loop_len']:<10} {result['total_states']:<8}")

        # 统计最终态一致性
        finals = [tuple(r['final']) for r in results]
        unique_finals = len(set(finals))

        # 统计循环长度一致性
        loop_lens = [r['loop_len'] for r in results]
        unique_loops = len(set(loop_lens))

        print(f"  {'结果一致性':<12}:")
        print(f"    最终态种类: {unique_finals}/10")
        print(f"    循环长度种类: {unique_loops}/10")

        return {
            'results': results,
            'unique_finals': unique_finals,
            'unique_loops': unique_loops,
        }

    def run(self):
        print("=" * 70)
        print("  全连接图主线长时间稳定性测试 (每分钟1次，共10次)")
        print("=" * 70)
        print(f"开始时间: {datetime.now()}")
        print(f"注意: 由于是模拟，实际间隔为0秒，仅记录运行时间戳")

        all_results = {}

        for name, entanglement in self.graphs.items():
            all_results[name] = self.test_long_term(name, entanglement)

        # 汇总
        print(f"\n{'='*70}")
        print("  全连接图主线汇总")
        print(f"{'='*70}")
        print(f"\n{'图组':<18} {'最终态种类':<12} {'循环长度种类':<12} {'稳定性评估':<15}")
        print("-" * 50)
        for name, r in all_results.items():
            stability = "非常稳定" if r['unique_finals'] == 1 else \
                       "较稳定" if r['unique_finals'] <= 3 else \
                       "不稳定" if r['unique_finals'] <= 7 else "极不稳定"
            print(f"{name:<18} {r['unique_finals']:<12} {r['unique_loops']:<12} {stability:<15}")

        print(f"\n完成时间: {datetime.now()}")
        return all_results


if __name__ == "__main__":
    exp = LongTermStability()
    results = exp.run()

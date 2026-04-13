#!/usr/bin/env python3
"""
========================================================
全连接图主线扫频频率变化测试
========================================================

测试不同扫频频率对系统动力学的影响：
1. 固定低频：syndrome % 7 (低位置权重)
2. 固定高频：syndrome % 3 (高位置权重)
3. 频率扫描：逐步改变频率范围
4. 频率噪声：频率随时间微小扰动
5. 多频率混合：同时使用多个频率
"""

import numpy as np
from datetime import datetime

class FrequencyVariationTest:
    def __init__(self):
        self.graphs = {
            '全连接图主线': {i: [j for j in range(7) if j != i] for i in range(7)},
            '对照-环形': {
                0: [1, 6], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5, 0],
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

    def evolve(self, code, entanglement, freq_func, max_iter=10000):
        """通用演化，freq_func决定每次翻转哪个位"""
        seen = {tuple(code): 0}
        history = [code]
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = freq_func(code, syndrome, i)
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                loop_len = i + 1 - seen[key]
                cycle_states = tuple(sorted(tuple(s) for s in history[seen[key]:]))
                return {
                    'loop_len': loop_len,
                    'total_states': len(seen),
                    'final': tuple(code),
                    'cycle_states': cycle_states,
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop_len': 0, 'total_states': len(seen), 'final': tuple(code)}

    def test_frequency(self, name, entanglement, freq_name, freq_func, runs=50):
        """测试某种频率策略"""
        np.random.seed(42)
        initial = [np.random.randint(0, 2) for _ in range(7)]

        results = []
        for _ in range(runs):
            result = self.evolve(initial.copy(), entanglement, freq_func)
            results.append({
                'loop_len': result['loop_len'],
                'total_states': result['total_states'],
                'cycle': result['cycle_states'],
            })

        unique_loops = len(set(r['loop_len'] for r in results))
        unique_states = len(set(r['total_states'] for r in results))
        unique_cycles = len(set(r['cycle'] for r in results))

        return {
            'initial': initial,
            'runs': runs,
            'unique_loops': unique_loops,
            'unique_states': unique_states,
            'unique_cycles': unique_cycles,
            'deterministic': unique_loops == 1 and unique_cycles == 1,
        }

    def run(self):
        print("=" * 70)
        print("  全连接图主线扫频频率变化测试")
        print("=" * 70)

        # 不同的频率策略
        freq_strategies = {
            '基准(syn%7)': lambda code, syn, i: syn % 7 if syn > 0 else i % 7,
            '固定低频(0)': lambda code, syn, i: 0,
            '固定中频(3)': lambda code, syn, i: 3,
            '固定高频(6)': lambda code, syn, i: 6,
            '位置循环': lambda code, syn, i: i % 7,
            '随机频率': lambda code, syn, i: np.random.randint(0, 7),
            '频率噪声(±1)': lambda code, syn, i: (syn + np.random.randint(-1, 2)) % 7 if syn > 0 else i % 7,
            '频率扫描': lambda code, syn, i: (i // 100) % 7,
        }

        all_results = {}

        for name, entanglement in self.graphs.items():
            print(f"\n{'='*70}")
            print(f"【{name}】")
            print(f"{'='*70}")

            graph_results = {}
            for freq_name, freq_func in freq_strategies.items():
                r = self.test_frequency(name, entanglement, freq_name, freq_func)
                graph_results[freq_name] = r

                det = "✓" if r['deterministic'] else "✗"
                print(f"\n  {freq_name}:")
                print(f"    唯一循环长度: {r['unique_loops']}")
                print(f"    唯一周期数: {r['unique_cycles']}")
                print(f"    确定性: {det}")

            all_results[name] = graph_results

        # 汇总表格
        print(f"\n{'='*70}")
        print("  全连接图主线频率策略汇总")
        print(f"{'='*70}")
        print(f"\n{'频率策略':<20} ", end="")
        for name in self.graphs.keys():
            print(f"{name[:6]:<8}", end="")
        print()
        print("-" * 50)

        for freq_name in freq_strategies.keys():
            print(f"{freq_name:<20} ", end="")
            for name in self.graphs.keys():
                det = "✓" if all_results[name][freq_name]['deterministic'] else "✗"
                print(f"{det:<8}", end="")
            print()

        # 循环长度分布
        print(f"\n{'='*70}")
        print("  全连接图主线各频率策略循环长度分布")
        print(f"{'='*70}")

        for name, entanglement in self.graphs.items():
            print(f"\n【{name}】")
            for freq_name, freq_func in freq_strategies.items():
                r = all_results[name][freq_name]
                print(f"  {freq_name}: 循环长度={r['unique_loops']}, 周期数={r['unique_cycles']}")

        return all_results


if __name__ == "__main__":
    exp = FrequencyVariationTest()
    results = exp.run()

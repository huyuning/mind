#!/usr/bin/env python3
"""
========================================================
全连接图主线扫频变化测试
========================================================

在扫频过程中引入不同的随机性/变化：
1. 随机error_pos：不用syndrome，改为随机选位
2. 概率性翻转：每次有一定概率翻转
3. 温度噪声：模拟热噪声
4. 频率漂移：模拟共振频率不稳定
"""

import numpy as np
from datetime import datetime

class ScanVariationTest:
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

    def evolve_deterministic(self, code, entanglement, max_iter=10000):
        """确定性：syndrome决定翻转位"""
        seen = {tuple(code): 0}
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                return {'loop_len': i + 1 - seen[key], 'total_states': len(seen), 'final': tuple(code)}
            code = next_code
            seen[key] = i + 1
        return {'loop_len': 0, 'total_states': len(seen), 'final': tuple(code)}

    def evolve_random_pos(self, code, entanglement, max_iter=10000):
        """随机翻转位：完全随机选位"""
        seen = {tuple(code): 0}
        for i in range(max_iter):
            error_pos = np.random.randint(0, 7)
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                return {'loop_len': i + 1 - seen[key], 'total_states': len(seen), 'final': tuple(code)}
            code = next_code
            seen[key] = i + 1
        return {'loop_len': 0, 'total_states': len(seen), 'final': tuple(code)}

    def evolve_probabilistic(self, code, entanglement, flip_prob=0.7, max_iter=10000):
        """概率性翻转：有flip_prob概率翻转"""
        seen = {tuple(code): 0}
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            if np.random.random() < flip_prob:
                code = self.resonance_flip(code, error_pos, entanglement)
            next_code = code
            key = tuple(next_code)
            if key in seen:
                return {'loop_len': i + 1 - seen[key], 'total_states': len(seen), 'final': tuple(code)}
            seen[key] = i + 1
        return {'loop_len': 0, 'total_states': len(seen), 'final': tuple(code)}

    def evolve_temperature(self, code, entanglement, temp=0.1, max_iter=10000):
        """温度噪声：概率翻转任意位"""
        seen = {tuple(code): 0}
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            code = self.resonance_flip(code, error_pos, entanglement)

            # 温度噪声：每个位有temp概率翻转
            for j in range(7):
                if np.random.random() < temp:
                    code[j] ^= 1

            key = tuple(code)
            if key in seen:
                return {'loop_len': i + 1 - seen[key], 'total_states': len(seen), 'final': tuple(code)}
            seen[key] = i + 1
        return {'loop_len': 0, 'total_states': len(seen), 'final': tuple(code)}

    def test_method(self, name, entanglement, method_name, evolve_func, runs=50):
        """测试某种方法"""
        np.random.seed(42)
        initial = [np.random.randint(0, 2) for _ in range(7)]

        results = []
        for _ in range(runs):
            result = evolve_func(initial.copy(), entanglement)
            results.append((result['loop_len'], result['total_states']))

        unique_loops = len(set(r[0] for r in results))
        unique_states = len(set(r[1] for r in results))

        return {
            'initial': initial,
            'runs': runs,
            'unique_loops': unique_loops,
            'unique_states': unique_states,
            'results': results,
        }

    def run(self):
        print("=" * 70)
        print("  全连接图主线扫频变化测试")
        print("=" * 70)

        methods = [
            ('确定性(syndrome)', self.evolve_deterministic),
            ('随机翻转位', self.evolve_random_pos),
            ('概率性翻转(70%)', lambda c, e: self.evolve_probabilistic(c, e, 0.7)),
            ('温度噪声(10%)', lambda c, e: self.evolve_temperature(c, e, 0.1)),
        ]

        all_results = {}

        for name, entanglement in self.graphs.items():
            print(f"\n{'='*70}")
            print(f"【{name}】")
            print(f"{'='*70}")

            graph_results = {}
            for method_name, method_func in methods:
                r = self.test_method(name, entanglement, method_name, method_func)
                graph_results[method_name] = r

                print(f"\n  {method_name}:")
                print(f"    初始态: {r['initial']}")
                print(f"    唯一循环长度数: {r['unique_loops']}")
                print(f"    唯一状态数: {r['unique_states']}")
                print(f"    确定性: {'✓' if r['unique_loops'] == 1 and r['unique_states'] == 1 else '✗'}")

            all_results[name] = graph_results

        # 汇总
        print(f"\n{'='*70}")
        print("  全连接图主线汇总")
        print(f"{'='*70}")
        print(f"\n{'图组':<18} {'确定性':<12} {'随机位':<12} {'概率翻转':<12} {'温度噪声':<12}")
        print("-" * 60)
        for name, gr in all_results.items():
            det = "✓" if gr['确定性(syndrome)']['unique_loops'] == 1 else "✗"
            rnd = "✓" if gr['随机翻转位']['unique_loops'] == 1 else "✗"
            prob = "✓" if gr['概率性翻转(70%)']['unique_loops'] == 1 else "✗"
            temp = "✓" if gr['温度噪声(10%)']['unique_loops'] == 1 else "✗"
            print(f"{name:<18} {det:<12} {rnd:<12} {prob:<12} {temp:<12}")

        return all_results


if __name__ == "__main__":
    exp = ScanVariationTest()
    results = exp.run()

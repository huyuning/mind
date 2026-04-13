#!/usr/bin/env python3
"""
========================================================
完全图抗温度干扰范围测试
========================================================

精确测试：找出完全图能保持确定性的噪声强度阈值
"""

import numpy as np
from datetime import datetime

class TemperatureRangeTest:
    def __init__(self):
        self.entanglement = {i: [j for j in range(7) if j != i] for i in range(7)}

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

    def evolve(self, code, max_iter=10000):
        seen = {tuple(code): 0}
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos)
            key = tuple(next_code)
            if key in seen:
                return {'final': tuple(code), 'loop_len': i + 1 - seen[key], 'states': len(seen)}
            code = next_code
            seen[key] = i + 1
        return {'final': tuple(code)}

    def test_temperature_range(self):
        """测试温度干扰范围"""
        print("=" * 70)
        print("  完全图抗温度干扰范围测试")
        print("=" * 70)

        np.random.seed(42)
        initial = [0, 0, 0, 0, 0, 0, 0]
        result_base = self.evolve(initial.copy())
        base_final = result_base['final']

        print(f"\n基准初始态: {initial}")
        print(f"基准终态: {base_final}")

        # 细粒度测试温度范围
        print(f"\n{'温度':<10} {'唯一终态':<12} {'回到基准':<10} {'稳定性'}")
        print("-" * 50)

        temp_levels = []
        for t in [0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]:
            finals = []
            for _ in range(100):
                np.random.seed(42 + _)
                noisy = initial.copy()
                for j in range(7):
                    if np.random.random() < t:
                        noisy[j] ^= 1
                result = self.evolve(noisy)
                finals.append(result['final'])

            unique = len(set(finals))
            back = base_final in finals
            stable = "✓ 稳定" if unique == 1 and back else "✗ 失稳"

            temp_levels.append((t, unique, back, stable))
            print(f"{t:<10.3f} {unique:<12} {back:<10} {stable}")

        # 找出临界点
        print(f"\n{'='*70}")
        print("  临界点分析")
        print(f"{'='*70}")

        stable_threshold = None
        for t, unique, back, stable in temp_levels:
            if unique == 1 and back:
                stable_threshold = t
                print(f"稳定阈值: t ≤ {t}")
                break

        if stable_threshold is None:
            for i, (t, unique, back, stable) in enumerate(temp_levels):
                if unique > 1 or not back:
                    print(f"失稳开始: t ≥ {t}")
                    if i > 0:
                        print(f"稳定阈值: {temp_levels[i-1][0]} < t < {t}")
                    break

        return temp_levels

    def test_attractor_robustness(self):
        """吸引子鲁棒性测试"""
        print(f"\n{'='*70}")
        print("  吸引子鲁棒性测试")
        print(f"{'='*70}")

        np.random.seed(42)
        initial = [0, 0, 0, 0, 0, 0, 0]
        result_base = self.evolve(initial.copy())
        base_final = result_base['final']

        print(f"基准吸引子: {base_final}")

        # 测试256种初始态
        print(f"\n256种初始态在不同温度下的吸引子数量:")
        print(f"{'温度':<10} {'吸引子数':<12} {'平均吸引子大小'}")
        print("-" * 40)

        for t in [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]:
            attractors = {}
            for n in range(256):
                code = [(n >> i) & 1 for i in range(7)]

                if t > 0:
                    np.random.seed(n)
                    for j in range(7):
                        if np.random.random() < t:
                            code[j] ^= 1

                result = self.evolve(code)
                attractors[result['final']] = attractors.get(result['final'], 0) + 1

            unique_attractors = len(attractors)
            avg_size = 256 / unique_attractors
            print(f"{t:<10.2f} {unique_attractors:<12} {avg_size:<15.1f}")


if __name__ == "__main__":
    exp = TemperatureRangeTest()
    exp.test_temperature_range()
    exp.test_attractor_robustness()
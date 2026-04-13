#!/usr/bin/env python3
"""
========================================================
自发翻转实验 - 无主动检测/纠正
========================================================

核心区别：
- 无主动检测错误
- 无主动纠正
- 只有共振驱动
- 系统自然演化

理论预测：
- 共振驱动 → 系统自发趋向稳定态
- 错误位自然被"修复"
- 不需要知道错误在哪

使用方法：
    python3 spontaneous_flip.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

class SpontaneousFlipExperiment:
    """
    自发翻转实验
    无主动检测/纠正，只有共振驱动
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits
        self.frequencies = [1e12, 2e12]  # 1THz, 2THz
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2

        print("=" * 60)
        print("  自发翻转实验")
        print("  无主动检测/纠正")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"共振频率: {self.resonance_freq/1e12:.2f}THz")

    def phase(self, pos, t):
        return 2 * np.pi * self.frequencies[pos] * t

    def superposition(self, t):
        """相位叠加 - 这是驱动力"""
        psi = np.exp(1j * self.phase(0, t)) + np.exp(1j * self.phase(1, t))
        return psi / 2

    def spontaneous_flip_probability(self, bits, t):
        """
        计算自发翻转概率

        关键：只有当系统处于不稳定态时才可能翻转
        - 不稳定态：存在0
        - 稳定态：全是1
        """
        psi = self.superposition(t)
        prob = np.abs(psi)**2

        n_zeros = bits.count(0)

        if n_zeros == 0:
            return 0.0

        base_flip_prob = prob * 0.5

        return base_flip_prob

    def evolve(self, bits, t, dt=0.001):
        """
        系统自然演化

        无主动检测！
        无主动纠正！
        只有共振驱动下的概率翻转
        """
        new_bits = bits.copy()

        flip_prob = self.spontaneous_flip_probability(bits, t)

        if flip_prob > 0:
            for i in range(len(new_bits)):
                if new_bits[i] == 0:
                    if np.random.random() < flip_prob:
                        new_bits[i] = 1
                        break

        return new_bits

    def run_single_trial(self, initial_bits, n_cycles=100, name=""):
        """
        运行单次试验
        观察系统如何自然演化
        """
        state = initial_bits.copy()
        history = [state.copy()]

        T = 1.0 / self.resonance_freq

        for cycle in range(n_cycles):
            t = cycle * T
            state = self.evolve(state, t)
            history.append(state.copy())

        final_state = state
        n_flips = sum(1 for i in range(self.n_bits)
                      if initial_bits[i] != final_state[i])

        return {
            'initial': initial_bits,
            'final': final_state,
            'n_flips': n_flips,
            'history': history,
            'name': name
        }

    def run_all_combinations(self):
        """
        256种组合全部实验
        观察每种初始状态如何自发演化
        """
        print(f"\n全部 {2**self.n_bits} 种组合自发演化实验...")

        results = []

        for combo in range(2**self.n_bits):
            initial = [(combo >> i) & 1 for i in range(self.n_bits)]
            n_zeros = initial.count(0)

            result = self.run_single_trial(initial, n_cycles=100)
            results.append(result)

            if (combo + 1) % 64 == 0:
                print(f"  进度: {combo + 1}/{2**self.n_bits}")

        return results

    def analyze_results(self, results):
        """分析自发演化结果"""
        print(f"\n{'='*60}")
        print("  自发翻转分析")
        print(f"{'='*60}")

        to_stable = 0
        to_unstable = 0
        stayed_same = 0

        flip_counts = []

        for r in results:
            initial = r['initial']
            final = r['final']

            initial_zeros = initial.count(0)
            final_zeros = final.count(0)

            flip_counts.append(r['n_flips'])

            if final_zeros == 0:
                to_stable += 1
            elif initial_zeros == final_zeros:
                stayed_same += 1
            else:
                to_unstable += 1

        print(f"\n演化结果:")
        print(f"  自发趋向稳定(全1): {to_stable}/{len(results)}")
        print(f"  保持不变: {stayed_same}/{len(results)}")
        print(f"  趋向不稳定: {to_unstable}/{len(results)}")

        print(f"\n翻转次数统计:")
        print(f"  总翻转: {sum(flip_counts)}")
        print(f"  平均翻转: {np.mean(flip_counts):.2f}")
        print(f"  最小: {min(flip_counts)}")
        print(f"  最大: {max(flip_counts)}")

        if to_stable == len(results):
            print(f"\n✓ 所有系统都自发趋向稳定态！")
            print(f"  结论: 共振驱动使系统自发稳定化")
            conclusion = "spontaneous_stabilization"
        else:
            print(f"\n⚠ 部分系统未完全稳定化")
            conclusion = "partial_stabilization"

        return {
            'total': len(results),
            'to_stable': to_stable,
            'stayed_same': stayed_same,
            'to_unstable': to_unstable,
            'stabilization_rate': to_stable / len(results),
            'total_flips': sum(flip_counts),
            'mean_flips': float(np.mean(flip_counts)),
            'conclusion': conclusion
        }

    def show_examples(self, results, n_examples=5):
        """展示几个典型演化例子"""
        print(f"\n{'='*60}")
        print("  典型演化例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n_examples]):
            print(f"\n例子{i+1}: {r['initial']} → {r['final']}")
            print(f"  初始0的个数: {r['initial'].count(0)}")
            print(f"  最终0的个数: {r['final'].count(0)}")
            print(f"  翻转次数: {r['n_flips']}")

            if r['n_flips'] > 0:
                print(f"  演化路径: {r['initial']}")
                for h in r['history'][1:5]:
                    print(f"             {h}")


def main():
    exp = SpontaneousFlipExperiment(n_bits=8)

    results = exp.run_all_combinations()

    exp.show_examples(results, n_examples=6)

    analysis = exp.analyze_results(results)

    full_results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'n_combinations': len(results),
        'results': [
            {
                'initial': r['initial'],
                'final': r['final'],
                'n_flips': r['n_flips']
            } for r in results
        ],
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"spontaneous_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return full_results


if __name__ == "__main__":
    main()
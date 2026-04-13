#!/usr/bin/env python3
"""
========================================================
笛卡尔积全实验 v2 - 全0/全1覆盖
========================================================

实验设计：
1. 全1张量，每位轮流放0错误
2. 全0张量，每位轮流放1错误
3. 所有可能组合(2^n张量)

使用方法：
    python3 resonance_cartesian_full.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path
from itertools import product

class FullCartesianExperiment:
    """
    全笛卡尔积实验
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits
        self.frequencies = [1e12, 2e12]
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2
        self.results = []

        print("=" * 60)
        print("  笛卡尔积全实验 v2")
        print("  全0/全1覆盖")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"理论组合数: 2^{n_bits} = {2**n_bits}")

    def phase(self, pos, t):
        return 2 * np.pi * self.frequencies[pos] * t

    def superposition(self, t):
        psi = np.exp(1j * self.phase(0, t)) + np.exp(1j * self.phase(1, t))
        return psi / 2

    def measure(self, bits, t, threshold=0.7):
        psi = self.superposition(t)
        prob = np.abs(psi)**2
        new_bits = bits.copy()

        if prob > threshold:
            for i in range(len(new_bits)):
                if bits[i] == 0:
                    new_bits[i] = 1
                    break

        return new_bits, prob

    def run_single(self, bits, n_cycles=100):
        state = bits.copy()
        flips = 0
        probs = []
        T = 1.0 / self.resonance_freq

        for i in range(n_cycles):
            t = i * T
            new_state, prob = self.measure(state, t)
            probs.append(prob)

            if new_state != state:
                flips += 1
                state = new_state

        return {
            'bits': bits,
            'n_flips': flips,
            'final_bits': state,
            'max_prob': max(probs),
            'min_prob': min(probs)
        }

    def run_all_ones_errors(self):
        """实验1: 全1张量，每位轮流放0"""
        print(f"\n{'='*50}")
        print("  实验1: 全1张量，每位轮流放0错误")
        print(f"{'='*50}")

        results = []
        for error_pos in range(self.n_bits):
            bits = [1] * self.n_bits
            bits[error_pos] = 0
            result = self.run_single(bits)
            results.append({
                'type': 'ones_with_zero',
                'error_pos': error_pos,
                'bits': bits,
                'result': result
            })
            print(f"  位置{error_pos}: {bits} → {result['n_flips']}次翻转")

        return results

    def run_all_zeros_errors(self):
        """实验2: 全0张量，每位轮流放1"""
        print(f"\n{'='*50}")
        print("  实验2: 全0张量，每位轮流放1错误")
        print(f"{'='*50}")

        results = []
        for error_pos in range(self.n_bits):
            bits = [0] * self.n_bits
            bits[error_pos] = 1
            result = self.run_single(bits)
            results.append({
                'type': 'zeros_with_one',
                'error_pos': error_pos,
                'bits': bits,
                'result': result
            })
            print(f"  位置{error_pos}: {bits} → {result['n_flips']}次翻转")

        return results

    def run_random_combinations(self, n_samples=32):
        """实验3: 随机采样部分组合"""
        print(f"\n{'='*50}")
        print(f"  实验3: 随机采样 {n_samples} 种组合")
        print(f"{'='*50}")

        results = []
        np.random.seed(42)

        all_combinations = list(product([0, 1], repeat=self.n_bits))

        sampled = np.random.choice(len(all_combinations), min(n_samples, len(all_combinations)), replace=False)

        for idx in sampled:
            bits = list(all_combinations[idx])
            result = self.run_single(bits)
            results.append({
                'type': 'random',
                'bits': bits,
                'result': result
            })

            if len(results) <= 8:
                print(f"  {bits} → {result['n_flips']}次翻转")

        if n_samples > 8:
            total_flips = sum(r['result']['n_flips'] for r in results)
            avg_flips = total_flips / len(results)
            print(f"  ... 共{len(results)}种，平均翻转: {avg_flips:.2f}")

        return results

    def analyze(self, results1, results2, results3):
        """分析所有结果"""
        print(f"\n{'='*60}")
        print("  汇总分析")
        print(f"{'='*60}")

        # 实验1分析
        flips1 = [r['result']['n_flips'] for r in results1]
        print(f"\n实验1 (全1+错误0):")
        print(f"  翻转: {flips1}")
        print(f"  总计: {sum(flips1)}")

        # 实验2分析
        flips2 = [r['result']['n_flips'] for r in results2]
        print(f"\n实验2 (全0+错误1):")
        print(f"  翻转: {flips2}")
        print(f"  总计: {sum(flips2)}")

        # 实验3分析
        flips3 = [r['result']['n_flips'] for r in results3]
        print(f"\n实验3 (随机组合):")
        print(f"  翻转: {flips3[:8]}...")
        print(f"  总计: {sum(flips3)}, 平均: {np.mean(flips3):.2f}")

        # 统计
        all_flips = flips1 + flips2 + flips3
        non_zero = sum(1 for f in all_flips if f > 0)
        zero = sum(1 for f in all_flips if f == 0)

        print(f"\n总统计:")
        print(f"  有翻转: {non_zero}")
        print(f"  无翻转: {zero}")
        print(f"  总实验: {len(all_flips)}")

        # 检查是否有无翻转的有错误张量
        errors_with_no_flip = 0
        for r in results1:
            if r['result']['n_flips'] == 0:
                errors_with_no_flip += 1
        for r in results2:
            if r['result']['n_flips'] == 0:
                errors_with_no_flip += 1

        print(f"\n  有错误但未翻转: {errors_with_no_flip} (应该为0)")

        return {
            'experiment1': {'flips': flips1, 'total': sum(flips1)},
            'experiment2': {'flips': flips2, 'total': sum(flips2)},
            'experiment3': {'flips': flips3, 'total': sum(flips3), 'avg': float(np.mean(flips3))},
            'errors_with_no_flip': errors_with_no_flip
        }


def main():
    exp = FullCartesianExperiment(n_bits=8)

    results1 = exp.run_all_ones_errors()
    results2 = exp.run_all_zeros_errors()
    results3 = exp.run_random_combinations(n_samples=32)

    analysis = exp.analyze(results1, results2, results3)

    full_results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'experiment1': results1,
        'experiment2': results2,
        'experiment3': results3,
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"cartesian_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return full_results


if __name__ == "__main__":
    main()
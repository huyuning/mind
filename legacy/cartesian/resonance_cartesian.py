#!/usr/bin/env python3
"""
========================================================
笛卡尔积全实验 - 每一位都有错误 vs 无错误对照
========================================================

对8位张量的每一位分别做实验：
- 每一位轮流放置错误
- 每个错误位置都有对应的无错误对照

使用方法：
    python3 resonance_cartesian.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path
from itertools import product

class CartesianResonanceExperiment:
    """
    笛卡尔积全实验
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits
        self.frequencies = [1e12, 2e12]  # 1THz, 2THz
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2
        self.results = []

        print("=" * 60)
        print("  笛卡尔积全实验")
        print("  每一位错误位置对照")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"频率: {self.frequencies[0]/1e12:.1f}THz, {self.frequencies[1]/1e12:.1f}THz")
        print(f"共振频率: {self.resonance_freq/1e12:.2f}THz")

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

    def create_error_tensor(self, error_pos):
        """创建指定错误位置的tensor"""
        bits = [1] * self.n_bits
        bits[error_pos] = 0
        return bits

    def create_no_error_tensor(self):
        """创建无错误tensor"""
        return [1] * self.n_bits

    def run_single_experiment(self, bits, name, n_cycles=100):
        """运行单个实验"""
        state = bits.copy()
        flips = []
        probs = []
        T = 1.0 / self.resonance_freq

        for i in range(n_cycles):
            t = i * T
            new_state, prob = self.measure(state, t)
            probs.append(prob)

            if new_state != state:
                flips.append({
                    'cycle': i,
                    'time_ps': t * 1e12,
                    'prob': prob
                })
                state = new_state

        return {
            'name': name,
            'initial_bits': bits,
            'final_bits': state,
            'n_flips': len(flips),
            'flip_cycles': [f['cycle'] for f in flips],
            'max_prob': max(probs),
            'min_prob': min(probs),
            'mean_prob': np.mean(probs)
        }

    def run_all_experiments(self, n_cycles=100):
        """
        笛卡尔积全实验
        对每一位：先做错误实验，再做无错误对照
        """
        print(f"\n{'='*60}")
        print("  开始全实验")
        print(f"{'='*60}")

        all_results = []

        for error_pos in range(self.n_bits):
            print(f"\n--- 位置 {error_pos} ---")

            # 实验1: 有错误
            error_bits = self.create_error_tensor(error_pos)
            error_result = self.run_single_experiment(
                error_bits,
                f"位置{error_pos}_有错误",
                n_cycles
            )
            all_results.append({
                'type': 'error',
                'position': error_pos,
                'result': error_result
            })
            print(f"  有错误: {error_result['n_flips']}次翻转")

            # 实验2: 无错误
            no_error_bits = self.create_no_error_tensor()
            no_error_result = self.run_single_experiment(
                no_error_bits,
                f"位置{error_pos}_无错误",
                n_cycles
            )
            all_results.append({
                'type': 'no_error',
                'position': error_pos,
                'result': no_error_result
            })
            print(f"  无错误: {no_error_result['n_flips']}次翻转")

        return all_results

    def analyze_results(self, all_results):
        """分析所有结果"""
        error_flips = []
        no_error_flips = []

        for r in all_results:
            if r['type'] == 'error':
                error_flips.append(r['result']['n_flips'])
            else:
                no_error_flips.append(r['result']['n_flips'])

        print(f"\n{'='*60}")
        print("  汇总分析")
        print(f"{'='*60}")

        print(f"\n有错误实验 ({self.n_bits}个):")
        print(f"  总翻转次数: {sum(error_flips)}")
        print(f"  位置翻转: {error_flips}")

        print(f"\n无错误对照 ({self.n_bits}个):")
        print(f"  总翻转次数: {sum(no_error_flips)}")
        print(f"  位置翻转: {no_error_flips}")

        # 统计正确预测
        correct_predictions = 0
        for i, r in enumerate(all_results):
            if r['type'] == 'error' and r['result']['n_flips'] > 0:
                correct_predictions += 1
            elif r['type'] == 'no_error' and r['result']['n_flips'] == 0:
                correct_predictions += 1

        total = len(all_results)
        accuracy = correct_predictions / total * 100

        print(f"\n正确预测: {correct_predictions}/{total} = {accuracy:.1f}%")

        return {
            'error_flips': error_flips,
            'no_error_flips': no_error_flips,
            'correct_predictions': correct_predictions,
            'total': total,
            'accuracy': accuracy
        }


def main():
    exp = CartesianResonanceExperiment(n_bits=8)
    all_results = exp.run_all_experiments(n_cycles=100)
    analysis = exp.analyze_results(all_results)

    results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'resonance_freq_thz': exp.resonance_freq / 1e12,
        'all_results': all_results,
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"cartesian_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    main()
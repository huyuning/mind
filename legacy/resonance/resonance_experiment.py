#!/usr/bin/env python3
"""
========================================================
共振翻转实验 - 有错误 vs 无错误对照
========================================================

实验设计：
1. 有错误张量 + 扫描 → 应该有翻转
2. 无错误张量 + 扫描 → 不应该有翻转

使用方法：
    python3 resonance_experiment.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

class ResonanceExperiment:
    """
    共振翻转实验
    """

    def __init__(self):
        self.frequencies = [1e12, 2e12]  # 1THz, 2THz
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2
        print("=" * 60)
        print("  共振翻转实验")
        print("  有错误 vs 无错误 对照")
        print("=" * 60)
        print(f"频率: {self.frequencies[0]/1e12:.1f}THz, {self.frequencies[1]/1e12:.1f}THz")
        print(f"共振频率: {self.resonance_freq/1e12:.2f}THz")

    def phase(self, pos, t):
        """相位"""
        return 2 * np.pi * self.frequencies[pos] * t

    def superposition(self, t):
        """叠加振幅"""
        psi = np.exp(1j * self.phase(0, t)) + np.exp(1j * self.phase(1, t))
        return psi / 2

    def measure(self, bits, t, threshold=0.7):
        """
        测量bits在时刻t的状态

        如果叠加概率 > threshold，发生翻转
        """
        psi = self.superposition(t)
        prob = np.abs(psi)**2

        new_bits = bits.copy()
        if prob > threshold:
            for i in range(len(new_bits)):
                if bits[i] == 0:
                    new_bits[i] = 1
                    break

        return new_bits, prob

    def run_experiment(self, bits, name, n_cycles=100):
        """
        运行单个实验
        """
        print(f"\n{'='*40}")
        print(f"  {name}")
        print(f"{'='*40}")
        print(f"初始状态: {bits}")

        state = bits.copy()
        probs = []
        flips = []

        T = 1.0 / self.resonance_freq

        for i in range(n_cycles):
            t = i * T
            new_state, prob = self.measure(state, t)

            probs.append(prob)

            if new_state != state:
                flips.append({
                    'cycle': i,
                    'time_ps': t * 1e12,
                    'prob': prob,
                    'from': state.copy(),
                    'to': new_state.copy()
                })
                state = new_state

            if i % 25 == 0:
                print(f"  Cycle {i:3d}: P={prob:.3f}, state={state}")

        print(f"\n结果:")
        print(f"  总周期: {n_cycles}")
        print(f"  翻转次数: {len(flips)}")
        print(f"  最大概率: {max(probs):.3f}")
        print(f"  最小概率: {min(probs):.3f}")

        return {
            'name': name,
            'initial_bits': bits,
            'final_bits': state,
            'n_flips': len(flips),
            'flip_events': flips,
            'probs': probs,
            'max_prob': max(probs),
            'min_prob': min(probs),
            'mean_prob': np.mean(probs)
        }


def main():
    exp = ResonanceExperiment()

    print("\n" + "=" * 60)
    print("  实验1: 有错误张量 (预期 → 有翻转)")
    print("=" * 60)

    bits_with_error = [1, 1, 1, 1, 1, 0, 1, 1]
    result1 = exp.run_experiment(bits_with_error, "有错误张量", n_cycles=100)

    print("\n" + "=" * 60)
    print("  实验2: 无错误张量 (预期 → 无翻转)")
    print("=" * 60)

    bits_no_error = [1, 1, 1, 1, 1, 1, 1, 1]
    result2 = exp.run_experiment(bits_no_error, "无错误张量", n_cycles=100)

    print("\n" + "=" * 60)
    print("  实验结论")
    print("=" * 60)

    print(f"\n有错误张量: {result1['n_flips']} 次翻转")
    print(f"无错误张量: {result2['n_flips']} 次翻转")

    if result1['n_flips'] > 0 and result2['n_flips'] == 0:
        print("\n✓ 理论得到支持!")
        print("  - 有错误张量发生翻转 ✓")
        print("  - 无错误张量未发生翻转 ✓")
        supported = True
    elif result2['n_flips'] > 0:
        print("\n✗ 理论被证伪!")
        print("  - 无错误张量不应该翻转!")
        supported = False
    else:
        print("\n⚠️ 结果不确定")
        print("  - 有错误张量应该翻转但没有")
        supported = None

    results = {
        'timestamp': datetime.now().isoformat(),
        'resonance_freq_thz': exp.resonance_freq / 1e12,
        'experiment_1_error': result1,
        'experiment_2_no_error': result2,
        'theory_supported': supported,
        'conclusion': '理论得到支持' if supported else ('理论被证伪' if supported == False else '结果不确定')
    }

    filepath = Path('./resonance_data') / f"resonance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n结果已保存: {filepath}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
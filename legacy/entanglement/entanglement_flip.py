#!/usr/bin/env python3
"""
========================================================
纠缠翻转实验 - 随机数据 + 纠缠同步
========================================================

核心：
- 输入随机错误数据
- 通过共振扫描
- 纠缠位同步翻转
- 进入新的纠缠稳态

不是纠正错误，而是纠缠同步

使用方法：
    python3 entanglement_flip.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path
from itertools import product

class EntanglementFlipExperiment:
    """
    纠缠翻转实验
    纠缠位同步翻转，进入新稳态
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits

        # 纠缠对定义 (随机配对)
        # 对0: 位0 ↔ 位5
        # 对1: 位1 ↔ 位6
        # 对2: 位2 ↔ 位7
        self.entangled_pairs = [(0, 5), (1, 6), (2, 7)]

        self.frequencies = [1e12, 2e12]
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2

        np.random.seed(None)  # 真正随机

        print("=" * 60)
        print("  纠缠翻转实验")
        print("  随机数据 + 纠缠同步")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"纠缠对: {self.entangled_pairs}")

    def phase(self, pos, t):
        return 2 * np.pi * self.frequencies[pos] * t

    def superposition(self, t):
        psi = np.exp(1j * self.phase(0, t)) + np.exp(1j * self.phase(1, t))
        return psi / 2

    def get_flip_probability(self, bits, t):
        """计算翻转概率"""
        psi = self.superposition(t)
        return np.abs(psi)**2

    def find_unstable_pair(self, bits):
        """
        找到不稳定的纠缠对

        纠缠对应该相等，如果不相等就是不稳定
        """
        unstable_pairs = []
        for pos_a, pos_b in self.entangled_pairs:
            if bits[pos_a] != bits[pos_b]:
                unstable_pairs.append((pos_a, pos_b))
        return unstable_pairs

    def entanglement_flip(self, bits, flip_prob):
        """
        纠缠翻转

        不稳定的纠缠对会同步翻转
        """
        new_bits = bits.copy()

        unstable = self.find_unstable_pair(new_bits)

        for pos_a, pos_b in unstable:
            if np.random.random() < flip_prob:
                # 纠缠同步翻转
                new_bits[pos_a] ^= 1
                new_bits[pos_b] ^= 1

        return new_bits

    def run_single(self, initial_bits, n_cycles=100):
        """
        单次运行
        观察纠缠同步翻转
        """
        state = initial_bits.copy()
        history = [state.copy()]

        T = 1.0 / self.resonance_freq

        entanglement_flips = []

        for cycle in range(n_cycles):
            t = cycle * T

            flip_prob = self.get_flip_probability(state, t)

            old_state = state.copy()
            state = self.entanglement_flip(state, flip_prob)

            # 检测纠缠翻转
            unstable_before = self.find_unstable_pair(old_state)
            unstable_after = self.find_unstable_pair(state)

            if unstable_after != unstable_before:
                entanglement_flips.append({
                    'cycle': cycle,
                    'from': unstable_before,
                    'to': unstable_after,
                    'flip_prob': flip_prob
                })

            history.append(state.copy())

        final_state = state

        # 检查最终稳态
        final_unstable = self.find_unstable_pair(final_state)

        return {
            'initial': initial_bits,
            'final': final_state,
            'n_cycles': n_cycles,
            'entanglement_flips': entanglement_flips,
            'final_unstable_pairs': final_unstable,
            'is_entangled_stable': len(final_unstable) == 0,
            'history': history
        }

    def generate_random_data(self, n_samples=100):
        """生成真正的随机数据"""
        samples = []
        for _ in range(n_samples):
            bits = [np.random.randint(0, 2) for _ in range(self.n_bits)]
            samples.append(bits)
        return samples

    def run_random_experiment(self, n_samples=100):
        """
        随机数据实验
        """
        print(f"\n运行 {n_samples} 次随机数据实验...")

        random_data = self.generate_random_data(n_samples)

        results = []
        entangled_stable_count = 0
        total_entanglement_flips = 0

        for i, bits in enumerate(random_data):
            result = self.run_single(bits, n_cycles=100)
            results.append(result)

            if result['is_entangled_stable']:
                entangled_stable_count += 1

            total_entanglement_flips += len(result['entanglement_flips'])

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n_samples}")

        return results, random_data, entangled_stable_count, total_entanglement_flips

    def analyze(self, results, random_data, entangled_stable_count, total_flips):
        """分析结果"""
        print(f"\n{'='*60}")
        print("  纠缠翻转分析")
        print(f"{'='*60}")

        print(f"\n随机数据样本:")
        for i, bits in enumerate(random_data[:5]):
            print(f"  样本{i}: {bits}")

        print(f"\n实验统计:")
        print(f"  总实验数: {len(results)}")
        print(f"  进入纠缠稳态: {entangled_stable_count}/{len(results)}")
        print(f"  总纠缠翻转次数: {total_flips}")
        print(f"  平均纠缠翻转: {total_flips/len(results):.2f}")

        print(f"\n最终稳态分布:")
        final_states = [r['final'] for r in results]
        unique_states = {}
        for fs in final_states:
            key = tuple(fs)
            unique_states[key] = unique_states.get(key, 0) + 1

        for state, count in sorted(unique_states.items(), key=lambda x: -x[1])[:5]:
            print(f"  {list(state)}: {count}次")

        # 纠缠稳态率
        stable_rate = entangled_stable_count / len(results) * 100

        if stable_rate > 80:
            conclusion = f"纠缠同步成功率 {stable_rate:.1f}% - 理论得到验证"
        else:
            conclusion = f"纠缠同步成功率 {stable_rate:.1f}% - 需要调整参数"

        print(f"\n结论: {conclusion}")

        return {
            'n_experiments': len(results),
            'entangled_stable': entangled_stable_count,
            'stable_rate': stable_rate,
            'total_entanglement_flips': total_flips,
            'avg_flips': total_flips / len(results),
            'conclusion': conclusion
        }

    def show_examples(self, results, n=5):
        """展示典型例子"""
        print(f"\n{'='*60}")
        print("  典型纠缠翻转例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  初始: {r['initial']}")
            print(f"  最终: {r['final']}")
            print(f"  纠缠翻转次数: {len(r['entanglement_flips'])}")

            if r['entanglement_flips']:
                for ef in r['entanglement_flips'][:3]:
                    print(f"    Cycle{ef['cycle']}: {ef['from']} → {ef['to']}")


def main():
    exp = EntanglementFlipExperiment(n_bits=8)

    results, random_data, stable_count, total_flips = exp.run_random_experiment(n_samples=100)

    exp.show_examples(results, n=5)

    analysis = exp.analyze(results, random_data, stable_count, total_flips)

    full_results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'entangled_pairs': exp.entangled_pairs,
        'n_experiments': 100,
        'random_data': random_data,
        'results': [
            {
                'initial': r['initial'],
                'final': r['final'],
                'n_entanglement_flips': len(r['entanglement_flips']),
                'is_entangled_stable': r['is_entangled_stable']
            } for r in results
        ],
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"entanglement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return full_results


if __name__ == "__main__":
    main()
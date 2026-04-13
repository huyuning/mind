#!/usr/bin/env python3
"""
========================================================
纠缠翻转实验 v2 - 跟随触发 + 随机数据
========================================================

核心：
- 随机数据作为输入
- 共振驱动导致自发翻转
- 纠缠位跟随翻转（不只是检测不等）
- 进入新的纠缠稳态

使用方法：
    python3 entanglement_flip_v2.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

class EntanglementFlipV2:
    """
    纠缠翻转实验 v2
    跟随触发机制
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits

        # 纠缠对: (位A, 位B)
        self.entangled_pairs = [(0, 5), (1, 6), (2, 7)]

        self.frequencies = [1e12, 2e12]
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2

        np.random.seed(None)

        print("=" * 60)
        print("  纠缠翻转实验 v2")
        print("  跟随触发 + 随机数据")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"纠缠对: {self.entangled_pairs}")

    def superposition(self, t):
        psi = np.exp(1j * 2 * np.pi * self.frequencies[0] * t)
        psi += np.exp(1j * 2 * np.pi * self.frequencies[1] * t)
        return psi / 2

    def resonance_flip(self, bits, t):
        """
        共振翻转 + 纠缠跟随

        1. 计算共振概率
        2. 如果触发翻转 → 纠缠位跟随翻转
        """
        new_bits = bits.copy()

        psi = self.superposition(t)
        prob = np.abs(psi)**2

        # 找到所有0的位置
        zero_positions = [i for i in range(self.n_bits) if bits[i] == 0]

        if zero_positions and np.random.random() < prob:
            # 随机选一个0翻转
            flip_pos = np.random.choice(zero_positions)

            # 找到flip_pos属于哪个纠缠对
            for pair in self.entangled_pairs:
                if flip_pos in pair:
                    # 纠缠跟随：同对的另一个也翻转
                    partner = pair[0] if pair[1] == flip_pos else pair[1]

                    new_bits[flip_pos] = 1
                    new_bits[partner] ^= 1  # 纠缠翻转

                    return new_bits, flip_pos, partner

            # 没有纠缠对，直接翻转
            new_bits[flip_pos] = 1

        return new_bits, -1, -1

    def run_single(self, initial_bits, n_cycles=100):
        """单次运行"""
        state = initial_bits.copy()
        history = [state.copy()]

        flips = []
        T = 1.0 / self.resonance_freq

        for cycle in range(n_cycles):
            t = cycle * T

            old_state = state.copy()
            state, flip_pos, partner = self.resonance_flip(state, t)

            if partner >= 0:
                flips.append({
                    'cycle': cycle,
                    'primary': flip_pos,
                    'entangled_partner': partner,
                    'from': old_state.copy(),
                    'to': state.copy()
                })

            history.append(state.copy())

        return {
            'initial': initial_bits,
            'final': state,
            'flips': flips,
            'n_flips': len(flips),
            'history': history
        }

    def run_random(self, n_samples=100):
        """随机数据实验"""
        print(f"\n运行 {n_samples} 次随机数据实验...")

        results = []

        for i in range(n_samples):
            # 真正随机数据
            bits = [np.random.randint(0, 2) for _ in range(self.n_bits)]

            result = self.run_single(bits, n_cycles=100)
            results.append({
                'initial': bits,
                'final': result['final'],
                'flips': result['flips'],
                'n_flips': result['n_flips']
            })

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n_samples}")

        return results

    def analyze(self, results):
        """分析"""
        print(f"\n{'='*60}")
        print("  纠缠翻转分析")
        print(f"{'='*60}")

        total_flips = sum(r['n_flips'] for r in results)
        samples_with_flips = sum(1 for r in results if r['n_flips'] > 0)

        print(f"\n实验统计:")
        print(f"  总实验数: {len(results)}")
        print(f"  有翻转的实验: {samples_with_flips}/{len(results)}")
        print(f"  总纠缠翻转: {total_flips}")
        print(f"  平均翻转: {total_flips/len(results):.2f}")

        # 纠缠跟随统计
        partner_flips = 0
        for r in results:
            for f in r['flips']:
                if f['entangled_partner'] >= 0:
                    partner_flips += 1

        print(f"  纠缠跟随翻转: {partner_flips}")

        # 统计最终状态
        final_states = {}
        for r in results:
            key = tuple(r['final'])
            final_states[key] = final_states.get(key, 0) + 1

        print(f"\n最终稳态分布 (Top 5):")
        for state, count in sorted(final_states.items(), key=lambda x: -x[1])[:5]:
            print(f"  {list(state)}: {count}次")

        # 检查纠缠稳态
        entangled_stable = 0
        for r in results:
            state = r['final']
            stable = True
            for a, b in self.entangled_pairs:
                if state[a] != state[b]:
                    stable = False
                    break
            if stable:
                entangled_stable += 1

        print(f"\n进入纠缠稳态: {entangled_stable}/{len(results)} = {entangled_stable/len(results)*100:.1f}%")

        return {
            'n_experiments': len(results),
            'experiments_with_flips': samples_with_flips,
            'total_flips': total_flips,
            'avg_flips': total_flips / len(results),
            'entangled_stable': entangled_stable,
            'stable_rate': entangled_stable / len(results) * 100
        }

    def show_examples(self, results, n=5):
        """展示例子"""
        print(f"\n{'='*60}")
        print("  纠缠翻转例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            if r['n_flips'] > 0:
                print(f"\n例子{i+1}: {r['initial']} → {r['final']}")
                print(f"  翻转次数: {r['n_flips']}")
                for f in r['flips'][:3]:
                    print(f"    Cycle{f['cycle']}: 位{f['primary']}翻转 → 纠缠位{f['entangled_partner']}跟随")


def main():
    exp = EntanglementFlipV2(n_bits=8)

    results = exp.run_random(n_samples=100)

    exp.show_examples(results)

    analysis = exp.analyze(results)

    full_results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'entangled_pairs': exp.entangled_pairs,
        'n_experiments': 100,
        'results': [
            {
                'initial': r['initial'],
                'final': r['final'],
                'n_flips': r['n_flips'],
                'flips': [{'cycle': f['cycle'], 'primary': f['primary'],
                          'partner': f['entangled_partner']} for f in r['flips']]
            } for r in results
        ],
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"entanglement_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return full_results


if __name__ == "__main__":
    main()
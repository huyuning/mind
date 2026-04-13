#!/usr/bin/env python3
"""
========================================================
纠缠翻转实验 v3 - 错误注入 + 纠缠跟随
========================================================

核心理解：
1. 随机数据作为"正确"基态
2. 注入一位错误
3. 共振扫描
4. 纠缠位跟随翻转
5. 进入新的纠缠稳态（不是纠正错误）

关键：最终态不是回到正确，而是新稳态

使用方法：
    python3 entanglement_flip_v3.py
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

class EntanglementFlipV3:
    """
    纠缠翻转实验 v3
    错误注入 + 纠缠跟随
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits

        # 纠缠对
        self.entangled_pairs = [(0, 5), (1, 6), (2, 7)]

        self.frequencies = [1e12, 2e12]
        self.resonance_freq = np.abs(self.frequencies[1] - self.frequencies[0]) / 2

        np.random.seed(None)

        print("=" * 60)
        print("  纠缠翻转实验 v3")
        print("  错误注入 + 纠缠跟随")
        print("=" * 60)
        print(f"位长度: {n_bits}")
        print(f"纠缠对: {self.entangled_pairs}")

    def superposition(self, t):
        psi = np.exp(1j * 2 * np.pi * self.frequencies[0] * t)
        psi += np.exp(1j * 2 * np.pi * self.frequencies[1] * t)
        return psi / 2

    def inject_error(self, bits, error_pos=None):
        """注入一位错误"""
        bits = bits.copy()

        if error_pos is None:
            error_pos = np.random.randint(0, self.n_bits)

        bits[error_pos] ^= 1
        return bits, error_pos

    def run_single_trial(self, correct_bits, error_pos=None, n_cycles=50):
        """
        单次试验

        1. 正确数据
        2. 注入错误
        3. 共振演化
        4. 观察最终态
        """
        # 注入错误
        error_bits, actual_error_pos = self.inject_error(correct_bits, error_pos)

        state = error_bits.copy()

        T = 1.0 / self.resonance_freq

        flip_record = []

        for cycle in range(n_cycles):
            t = cycle * T

            psi = self.superposition(t)
            prob = np.abs(psi)**2

            # 找到纠缠对中不相等的
            unstable_pairs = []
            for a, b in self.entangled_pairs:
                if state[a] != state[b]:
                    unstable_pairs.append((a, b))

            # 如果有不稳定的纠缠对，且概率触发
            if unstable_pairs and np.random.random() < prob:
                # 随机选一个不稳定的对
                pair = unstable_pairs[np.random.randint(0, len(unstable_pairs))]

                # 两个位都翻转
                state[pair[0]] ^= 1
                state[pair[1]] ^= 1

                flip_record.append({
                    'cycle': cycle,
                    'pair': pair,
                    'from': [error_bits[p] for p in pair],
                    'to': [state[p] for p in pair]
                })

        # 检查最终纠缠稳态
        final_stable = True
        for a, b in self.entangled_pairs:
            if state[a] != state[b]:
                final_stable = False
                break

        return {
            'correct': correct_bits,
            'error_injected': error_bits,
            'actual_error_pos': actual_error_pos,
            'final': state,
            'flip_record': flip_record,
            'n_flips': len(flip_record),
            'is_entangled_stable': final_stable
        }

    def run_experiment(self, n_trials=100):
        """运行实验"""
        print(f"\n运行 {n_trials} 次实验...")

        results = []

        for i in range(n_trials):
            # 随机正确数据
            correct_bits = [np.random.randint(0, 2) for _ in range(self.n_bits)]

            result = self.run_single_trial(correct_bits, n_cycles=50)
            results.append(result)

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n_trials}")

        return results

    def analyze(self, results):
        """分析"""
        print(f"\n{'='*60}")
        print("  实验分析")
        print(f"{'='*60}")

        n_stable = sum(1 for r in results if r['is_entangled_stable'])
        total_flips = sum(r['n_flips'] for r in results)

        print(f"\n实验统计:")
        print(f"  总实验: {len(results)}")
        print(f"  进入纠缠稳态: {n_stable}/{len(results)} = {n_stable/len(results)*100:.1f}%")
        print(f"  总翻转次数: {total_flips}")
        print(f"  平均翻转: {total_flips/len(results):.2f}")

        # 检查最终态 vs 正确态
        back_to_correct = 0
        new_stable = 0

        for r in results:
            if r['final'] == r['correct']:
                back_to_correct += 1
            elif r['is_entangled_stable']:
                new_stable += 1

        print(f"\n最终态分析:")
        print(f"  回到正确态: {back_to_correct}/{len(results)}")
        print(f"  进入新稳态: {new_stable}/{len(results)}")
        print(f"  未稳定: {len(results) - back_to_correct - new_stable}/{len(results)}")

        # 最终态分布
        final_states = {}
        for r in results:
            key = tuple(r['final'])
            final_states[key] = final_states.get(key, 0) + 1

        print(f"\n最终态分布 (Top 5):")
        for state, count in sorted(final_states.items(), key=lambda x: -x[1])[:5]:
            print(f"  {list(state)}: {count}次")

        return {
            'n_trials': len(results),
            'entangled_stable': n_stable,
            'stable_rate': n_stable / len(results) * 100,
            'total_flips': total_flips,
            'avg_flips': total_flips / len(results),
            'back_to_correct': back_to_correct,
            'new_stable': new_stable
        }

    def show_examples(self, results, n=5):
        """展示例子"""
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  正确:  {r['correct']}")
            print(f"  错误:  {r['error_injected']} (位{r['actual_error_pos']}翻转)")
            print(f"  最终:  {r['final']}")
            print(f"  翻转:  {r['n_flips']}次")

            if r['flip_record']:
                for fr in r['flip_record'][:2]:
                    print(f"    Cycle{fr['cycle']}: 对{fr['pair']}: {fr['from']}→{fr['to']}")


def main():
    exp = EntanglementFlipV3(n_bits=8)

    results = exp.run_experiment(n_trials=100)

    exp.show_examples(results, n=5)

    analysis = exp.analyze(results)

    full_results = {
        'timestamp': datetime.now().isoformat(),
        'n_bits': 8,
        'entangled_pairs': exp.entangled_pairs,
        'n_trials': 100,
        'results': [
            {
                'correct': r['correct'],
                'error_injected': r['error_injected'],
                'final': r['final'],
                'n_flips': r['n_flips'],
                'is_entangled_stable': r['is_entangled_stable']
            } for r in results
        ],
        'analysis': analysis
    }

    filepath = Path('./resonance_data') / f"entanglement_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  结果已保存: {filepath}")
    print(f"{'='*60}")

    return full_results


if __name__ == "__main__":
    main()
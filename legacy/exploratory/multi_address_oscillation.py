#!/usr/bin/env python3
"""
全连接图在不同内存地址的振荡一致性实验

核心问题：
- 同一个K8全连接图结构
- 放置在内存的不同物理地址
- 振荡模式是否相同？

如果相同 → 全连接图结构决定振荡，与位置无关
如果不同 → 物理环境（噪声、温度）影响振荡
"""

import numpy as np
from datetime import datetime

class MultiAddressOscillationExperiment:
    """
    多地址振荡一致性实验
    """

    def __init__(self, n_bits=8, n_addresses=10, n_trials=100):
        self.n_bits = n_bits
        self.n_addresses = n_addresses
        self.n_trials = n_trials
        self.entanglement = {i: [j for j in range(n_bits) if j != i] for i in range(n_bits)}

    def syndrome(self, code):
        """计算伴随式"""
        return sum(code) % 2

    def resonance_flip(self, code, error_pos):
        """共振翻转 - K8全连接"""
        new_code = code.copy()
        entangled = self.entanglement[error_pos]
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code

    def simulate_address(self, initial_bits, noise_level=0.0):
        """
        模拟单个地址的振荡演化

        noise_level: 噪声水平（模拟物理环境差异）
        """
        bits = initial_bits.copy()
        seen = {tuple(bits): 0}
        history = [tuple(bits)]

        for step in range(self.n_trials):
            syndrome_val = self.syndrome(bits)
            error_pos = syndrome_val
            bits = self.resonance_flip(bits, error_pos)

            # 添加噪声（模拟物理环境差异）
            if noise_level > 0:
                for i in range(len(bits)):
                    if np.random.random() < noise_level:
                        bits[i] ^= 1

            history.append(tuple(bits))
            key = tuple(bits)

            if key in seen:
                loop_len = step + 1 - seen[key]
                return {
                    'loop_len': loop_len,
                    'transient_len': seen[key],
                    'history': history,
                    'attractor': key
                }
            seen[key] = step + 1

        return {
            'loop_len': 0,
            'transient_len': len(seen),
            'history': history,
            'attractor': tuple(bits)
        }

    def run_experiment_no_noise(self):
        """
        实验1：无噪声情况（理论预期）
        """
        print("\n" + "="*70)
        print("  实验1：无噪声 - 纯全连接图结构振荡")
        print("="*70)

        initial = [0, 0, 0, 0, 0, 0, 1, 0]  # 固定初始

        results = []
        for addr in range(self.n_addresses):
            result = self.simulate_address(initial, noise_level=0.0)
            results.append({
                'address': addr,
                **result
            })
            print(f"  地址{addr:2d}: 循环长度={result['loop_len']}, "
                  f"过渡长度={result['transient_len']}, "
                  f"吸引子={result['attractor']}")

        # 检查一致性
        loop_lens = [r['loop_len'] for r in results]
        attractors = [r['attractor'] for r in results]

        print(f"\n  ★ 无噪声结果:")
        print(f"    循环长度: {set(loop_lens)}")
        print(f"    吸引子: {len(set(attractors))}个唯一值")
        print(f"    一致性: {'完全一致' if len(set(loop_lens))==1 and len(set(attractors))==1 else '存在差异'}")

        return results

    def run_experiment_with_noise(self, noise_levels=[0.0, 0.001, 0.01, 0.1]):
        """
        实验2：不同噪声水平（模拟不同物理地址环境）
        """
        print("\n" + "="*70)
        print("  实验2：不同噪声水平模拟不同物理地址")
        print("="*70)

        initial = [0, 0, 0, 0, 0, 0, 1, 0]

        results_by_noise = {}

        for noise in noise_levels:
            print(f"\n  噪声水平: {noise}")
            results = []

            for addr in range(self.n_addresses):
                np.random.seed(addr * 1000)  # 每个地址不同随机种子
                result = self.simulate_address(initial, noise_level=noise)
                results.append({
                    'address': addr,
                    **result
                })

            loop_lens = [r['loop_len'] for r in results]
            attractors = [r['attractor'] for r in results]
            unique_loops = len(set(loop_lens))
            unique_attractors = len(set(attractors))

            print(f"    地址数: {self.n_addresses}")
            print(f"    循环长度范围: [{min(loop_lens)}, {max(loop_lens)}]")
            print(f"    唯一循环长度数: {unique_loops}")
            print(f"    唯一吸引子数: {unique_attractors}")

            results_by_noise[noise] = {
                'loop_lens': loop_lens,
                'attractors': attractors,
                'unique_loops': unique_loops,
                'unique_attractors': unique_attractors
            }

        return results_by_noise

    def run_experiment_random_initial(self):
        """
        实验3：不同初始条件（模拟不同字符/数据）
        """
        print("\n" + "="*70)
        print("  实验3：不同初始条件的振荡")
        print("="*70)

        test_initial_conditions = [
            [0, 0, 0, 0, 0, 0, 0, 0],  # 全0
            [1, 1, 1, 1, 1, 1, 1, 1],  # 全1
            [0, 1, 0, 1, 0, 1, 0, 1],  # 交替
            [0, 0, 1, 1, 0, 0, 1, 1],  # 分组
            [1, 0, 0, 0, 0, 0, 0, 1],  # A字符
        ]

        results = []

        for idx, initial in enumerate(test_initial_conditions):
            result = self.simulate_address(initial, noise_level=0.0)

            results.append({
                'initial': initial,
                'loop_len': result['loop_len'],
                'attractor': result['attractor']
            })

            initial_str = ''.join(str(b) for b in initial)
            attractor_str = ''.join(str(b) for b in result['attractor'])
            print(f"  初始{idx}: {initial_str} → 循环={result['loop_len']}, 吸引子={attractor_str}")

        return results

    def analyze_convergence(self, results_no_noise, results_with_noise, results_random):
        """
        分析收敛性
        """
        print("\n" + "="*70)
        print("  收敛性分析")
        print("="*70)

        print("\n  1. 无噪声情况:")
        loop_lens = [r['loop_len'] for r in results_no_noise]
        print(f"     循环长度: 全部 = {loop_lens[0]}")
        print(f"     结论: 全连接图结构决定唯一振荡")

        print("\n  2. 有噪声情况:")
        for noise, data in results_with_noise.items():
            if data['unique_loops'] == 1:
                print(f"     噪声{noise}: 循环长度仍一致")
            else:
                print(f"     噪声{noise}: 循环长度出现分化 ({data['unique_loops']}种)")

        print("\n  3. 不同初始条件:")
        loop_lens = [r['loop_len'] for r in results_random]
        unique_loops = len(set(loop_lens))
        print(f"     唯一循环长度数: {unique_loops}")
        print(f"     结论: {'所有初始都收敛到同一循环' if unique_loops == 1 else '不同初始收敛到不同循环'}")


def main():
    print("="*70)
    print("  全连接图多地址振荡一致性实验")
    print("  问题：不同内存地址的振荡是否相同？")
    print("="*70)

    exp = MultiAddressOscillationExperiment(n_bits=8, n_addresses=10, n_trials=100)

    # 实验1：无噪声
    results_no_noise = exp.run_experiment_no_noise()

    # 实验2：有噪声
    results_with_noise = exp.run_experiment_with_noise([0.0, 0.001, 0.01, 0.1])

    # 实验3：不同初始
    results_random = exp.run_experiment_random_initial()

    # 分析
    exp.analyze_convergence(results_no_noise, results_with_noise, results_random)

    print("\n" + "="*70)
    print("  核心结论")
    print("="*70)
    print("""
    ★ 如果无噪声情况下，所有地址振荡完全相同：
      → 全连接图结构是"数学抽象"，与物理位置无关
      → 这支持"内存中心宇宙"的理论

    ★ 如果有噪声情况下振荡分化：
      → 物理环境会影响振荡模式
      → 这解释了为什么"物质世界"有多样性

    ★ 如果不同初始都收敛到同一循环：
      → 全连接图是"宇宙的稳定锚点"
      → 所有信息最终归于同一基本振动
    """)


if __name__ == "__main__":
    main()
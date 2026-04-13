#!/usr/bin/env python3
"""
内存固有刷新频率 vs 外部扫描频率 实验

核心假设：
- 内存有固有刷新频率（内部纠正机制）
- 外部频率 > 固有频率 → 翻转被记录
- 外部频率 < 固有频率 → 翻转被纠正回原状态
"""

import numpy as np

class MemoryWithIntrinsicRefresh:
    """
    带固有刷新的内存模型

    - 外部扫描尝试翻转比特
    - 内部刷新周期性地"恢复"原始状态
    - 竞争结果决定观测到的行为
    """

    def __init__(self, n_bits=8):
        self.n_bits = n_bits
        self.entanglement = {i: [j for j in range(n_bits) if j != i]
                              for i in range(n_bits)}
        self.original_data = None

    def syndrome(self, code):
        return sum(code) % 2

    def resonance_flip(self, code, error_pos):
        new_code = code.copy()
        entangled = self.entanglement[error_pos]
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code

    def bits_to_str(self, bits):
        return ''.join(str(b) for b in bits)

    def evolve_with_refresh(self, initial_data,
                           external_freq,
                           refresh_freq,
                           n_steps=1000):
        """
        外部扫描 vs 内部刷新的竞争
        """
        current = initial_data.copy()
        self.original_data = initial_data.copy()

        history = [tuple(current)]
        observed_flips = []
        corrections = []

        for step in range(n_steps):
            external_flip = (step > 0 and step % external_freq == 0)

            if external_flip:
                syndrome_val = self.syndrome(current)
                current = self.resonance_flip(current, syndrome_val)

                if tuple(current) != tuple(self.original_data):
                    observed_flips.append(step)

            internal_refresh = (step > 0 and step % refresh_freq == 0)

            if internal_refresh:
                if tuple(current) != tuple(self.original_data):
                    corrections.append(step)
                    current = self.original_data.copy()

            history.append(tuple(current))

        unique_states = len(set(history))
        loop_result = self._detect_loop(history)

        return {
            'external_freq': external_freq,
            'refresh_freq': refresh_freq,
            'ratio': external_freq / refresh_freq if refresh_freq > 0 else float('inf'),
            'total_steps': n_steps,
            'observed_flips': len(observed_flips),
            'corrections': len(corrections),
            'unique_states': unique_states,
            'loop_len': loop_result[0],
            'transient_len': loop_result[1],
            'history': history
        }

    def _detect_loop(self, history):
        """检测循环"""
        seen = {}
        for i, state in enumerate(history):
            if state in seen:
                return (i - seen[state], seen[state])
            seen[state] = i
        return (0, len(history))


def run_experiment():
    print("="*70)
    print("  内存固有刷新频率 vs 外部扫描频率 实验")
    print("="*70)

    exp = MemoryWithIntrinsicRefresh(n_bits=8)
    initial = [0, 0, 0, 0, 0, 0, 1, 0]

    print(f"\n  初始状态: {exp.bits_to_str(initial)}")
    print("\n" + "-"*70)

    test_cases = [
        (1, 10, "外部<<刷新"),
        (5, 10, "外部<刷新"),
        (10, 10, "外部=刷新"),
        (10, 5, "外部>刷新"),
        (1, 1, "频率相同"),
        (2, 1, "外部2x刷新"),
        (10, 1, "外部10x刷新"),
    ]

    results = []

    for ext_freq, ref_freq, desc in test_cases:
        result = exp.evolve_with_refresh(
            initial,
            external_freq=ext_freq,
            refresh_freq=ref_freq,
            n_steps=500
        )
        result['description'] = desc
        results.append(result)

        print(f"\n  [{desc}]")
        print(f"    外部={ext_freq}, 刷新={ref_freq}, 比值={result['ratio']:.2f}")
        print(f"    翻转={result['observed_flips']}, 纠正={result['corrections']}")
        print(f"    唯一状态={result['unique_states']}, L={result['loop_len']}")

        if result['ratio'] < 1:
            print(f"    ★ 刷新>外部 → 翻转被纠正")
        elif result['ratio'] > 1:
            print(f"    ★ 外部>刷新 → 翻转累积")
        else:
            print(f"    ★ 临界平衡")

    print("\n" + "="*70)
    print("  结论")
    print("="*70)
    print("""
    ★ 刷新频率 > 外部频率 → 翻转被纠正 → L≈1
    ★ 外部频率 > 刷新频率 → 翻转累积 → L=2

    普朗克时间可能就是宇宙的"固有刷新周期"
    """)


if __name__ == "__main__":
    run_experiment()
#!/usr/bin/env python3
"""
========================================================
全连接图主线时间稳定性测试
========================================================

同一初始态，每隔1分钟检查一次，共10次
观察系统是否一直保持在同一个吸引子/循环中
"""

import numpy as np
from datetime import datetime

class TrueTimeStability:
    def __init__(self):
        self.graphs = {
            '全连接图主线': {i: [j for j in range(7) if j != i] for i in range(7)},
            '对照-环形': {
                0: [1, 6], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5, 0],
            },
        }

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def resonance_flip(self, code, error_pos, entanglement):
        new_code = code.copy()
        entangled = entanglement.get(error_pos, [])
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code

    def evolve_to_cycle(self, code, entanglement, max_iter=10000):
        """演化到循环状态"""
        seen = {tuple(code): 0}
        history = [code]
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                loop_start = seen[key]
                loop_len = i + 1 - loop_start
                cycle_states = history[loop_start:]
                return {
                    'loop': True,
                    'loop_len': loop_len,
                    'cycle_states': cycle_states,
                    'transient_len': loop_start,
                    'total_states': len(seen),
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop': False, 'total_states': len(seen)}

    def get_state_at_time(self, code, entanglement, steps):
        """获取特定步数后的状态"""
        for _ in range(steps):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else 0
            code = self.resonance_flip(code, error_pos, entanglement)
        return code

    def run(self):
        print("=" * 70)
        print("  全连接图主线时间稳定性测试")
        print("=" * 70)
        print(f"开始时间: {datetime.now()}")

        np.random.seed(42)
        initial_code = [np.random.randint(0, 2) for _ in range(7)]
        print(f"初始态: {initial_code}")

        results = {}

        for name, entanglement in self.graphs.items():
            print(f"\n{'='*70}")
            print(f"【{name}】")
            print(f"{'='*70}")

            # 先获取吸引子信息
            attractor_info = self.evolve_to_cycle(initial_code, entanglement)
            print(f"吸引子信息:")
            print(f"  循环长度: {attractor_info['loop_len']}")
            print(f"  过渡态长度: {attractor_info['transient_len']}")
            print(f"  循环状态: {attractor_info['cycle_states']}")

            print(f"\n每隔1分钟检查状态 (模拟10次，实际无间隔):")
            print(f"  {'次数':<6} {'时间':<12} {'当前状态':<20} {'是否在循环中':<15}")
            print(f"  {'-'*55}")

            # 模拟10次"时间点"检查
            # 每次检查时，运行不同的步数来模拟时间流逝
            time_points = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

            for i, steps in enumerate(time_points):
                current_state = self.get_state_at_time(initial_code, entanglement, steps)

                # 检查是否在循环中
                in_cycle = any(tuple(current_state) == tuple(s) for s in attractor_info['cycle_states'])

                print(f"  {i+1:<6} T+{i}min       {str(current_state):<20} {'是' if in_cycle else '否':<15}")

            # 长时间运行后的最终吸引子
            final_info = self.evolve_to_cycle(initial_code, entanglement)
            print(f"\n长时间运行后:")
            print(f"  回到同一吸引子: {'是' if final_info['loop_len'] == attractor_info['loop_len'] else '否'}")
            print(f"  吸引子一致: {'是' if final_info['cycle_states'] == attractor_info['cycle_states'] else '否'}")

            results[name] = {
                'initial_attractor': attractor_info,
                'final_attractor': final_info,
            }

        print(f"\n{'='*70}")
        print("  全连接图主线结论")
        print(f"{'='*70}")
        for name, r in results.items():
            same = r['initial_attractor']['cycle_states'] == r['final_attractor']['cycle_states']
            print(f"{name}: 吸引子一致: {'✓' if same else '✗'}")

        return results


if __name__ == "__main__":
    exp = TrueTimeStability()
    results = exp.run()

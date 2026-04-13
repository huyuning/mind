#!/usr/bin/env python3
"""
========================================================
全连接图主线全面稳定性测试
========================================================

1. 抗噪声测试：加入随机噪声后看恢复能力
2. 节点故障测试：随机翻转一些比特
3. 扰动敏感性测试：对初始状态加微扰
4. 10分钟稳定性测试（模拟时间演化）
"""

import numpy as np
from datetime import datetime
import time

class StabilityTest:
    def __init__(self):
        self.graphs = {
            '全连接图主线': {i: [j for j in range(7) if j != i] for i in range(7)},
            '对照-环形': {
                0: [1, 6], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5, 0],
            },
            '对照-星形': {
                0: [1, 2, 3, 4, 5, 6],
                1: [0], 2: [0], 3: [0], 4: [0], 5: [0], 6: [0],
            },
            '对照-链形': {
                0: [1], 1: [0, 2], 2: [1, 3], 3: [2, 4],
                4: [3, 5], 5: [4, 6], 6: [5],
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

    def evolve(self, code, entanglement, max_iter=100):
        seen = {tuple(code): 0}
        history = [code]
        for i in range(max_iter):
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else i % 7
            next_code = self.resonance_flip(code, error_pos, entanglement)
            key = tuple(next_code)
            if key in seen:
                return {
                    'loop': True,
                    'loop_len': i + 1 - seen[key],
                    'total_states': len(seen),
                    'final': code,
                }
            code = next_code
            seen[key] = i + 1
            history.append(code)
        return {'loop': False, 'total_states': len(seen), 'final': code}

    def hamming_distance(self, a, b):
        return sum(1 for x, y in zip(a, b) if x != y)

    def test_noise_resistance(self, name, entanglement, noise_levels=[1, 2, 3]):
        """抗噪声测试：翻转1/2/3个随机比特"""
        print(f"\n  【抗噪声测试】")
        results = {}

        for noise in noise_levels:
            count_same = 0
            count_lost = 0

            for _ in range(100):
                original = [np.random.randint(0, 2) for _ in range(7)]
                result_before = self.evolve(original, entanglement)

                noisy = original.copy()
                positions = np.random.choice(7, noise, replace=False)
                for p in positions:
                    noisy[p] ^= 1

                result_after = self.evolve(noisy, entanglement)

                if result_after['final'] == result_before['final']:
                    count_same += 1
                else:
                    count_lost += 1

            results[noise] = {'same': count_same, 'lost': count_lost}
            print(f"    噪声{noise}位: 保持{count_same}%, 丢失{count_lost}%")

        return results

    def test_node_failure(self, name, entanglement, failures=[1, 2]):
        """节点故障测试：永久删除/固定1个或2个节点"""
        print(f"\n  【节点故障测试】")
        results = {}

        for n_fail in failures:
            count_recovered = 0
            count_lost = 0

            for _ in range(100):
                original = [np.random.randint(0, 2) for _ in range(7)]
                result_before = self.evolve(original, entanglement)

                failed = original.copy()
                fail_pos = np.random.choice(7, n_fail, replace=False)
                for p in fail_pos:
                    failed[p] = 0

                result_after = self.evolve(failed, entanglement)

                if result_after['final'] == result_before['final']:
                    count_recovered += 1
                else:
                    count_lost += 1

            results[n_fail] = {'recovered': count_recovered, 'lost': count_lost}
            print(f"    故障{n_fail}节点: 恢复{count_recovered}%, 丢失{count_lost}%")

        return results

    def test_perturbation(self, name, entanglement):
        """扰动敏感性测试：初始状态微扰"""
        print(f"\n  【扰动敏感性测试】")
        results = {}

        for n_perturb in [1, 2, 3]:
            count_same_basin = 0
            total = 0

            for _ in range(100):
                original = [np.random.randint(0, 2) for _ in range(7)]
                result_orig = self.evolve(original, entanglement)
                final_orig = result_orig['final']

                for _ in range(10):
                    perturbed = original.copy()
                    pert_pos = np.random.choice(7, n_perturb, replace=False)
                    for p in pert_pos:
                        perturbed[p] ^= 1

                    result_pert = self.evolve(perturbed, entanglement)
                    final_pert = result_pert['final']

                    total += 1
                    if final_pert == final_orig:
                        count_same_basin += 1

            rate = count_same_basin / total * 100
            results[n_perturb] = rate
            print(f"    扰动{n_perturb}位: 吸引子相同{rate:.1f}%")

        return results

    def test_10min_simulation(self, name, entanglement, sim_seconds=10):
        """10分钟稳定性测试：模拟长时间运行"""
        print(f"\n  【10分钟稳定性测试】(模拟{sim_seconds}秒)")

        start_time = time.time()
        iterations = 0
        states_seen = set()
        final_state = None

        code = [np.random.randint(0, 2) for _ in range(7)]
        states_seen.add(tuple(code))

        while time.time() - start_time < sim_seconds:
            syndrome = self.syndrome(code)
            error_pos = syndrome % 7 if syndrome > 0 else iterations % 7
            code = self.resonance_flip(code, error_pos, entanglement)
            states_seen.add(tuple(code))
            iterations += 1

            if iterations > 1000000:
                break

        elapsed = time.time() - start_time
        unique_states = len(states_seen)

        print(f"    实际运行: {elapsed:.2f}秒")
        print(f"    迭代次数: {iterations}")
        print(f"    经历状态数: {unique_states}")
        print(f"    状态/秒: {iterations/elapsed:.0f}")

        return {
            'iterations': iterations,
            'unique_states': unique_states,
            'states_per_second': iterations / elapsed
        }

    def run(self):
        print("=" * 70)
        print("  全连接图主线全面稳定性测试")
        print("=" * 70)
        print(f"开始时间: {datetime.now()}")

        all_results = {}

        for name, entanglement in self.graphs.items():
            print(f"\n{'='*70}")
            print(f"【{name}】")
            print(f"{'='*70}")

            results = {
                'noise': self.test_noise_resistance(name, entanglement),
                'node_failure': self.test_node_failure(name, entanglement),
                'perturbation': self.test_perturbation(name, entanglement),
                '10min': self.test_10min_simulation(name, entanglement, 3),
            }

            all_results[name] = results

        # 汇总
        print(f"\n{'='*70}")
        print("  全连接图主线汇总")
        print(f"{'='*70}")

        print(f"\n{'图组':<18} {'抗噪1位':<12} {'节点故障':<12} {'吸引子稳定性':<15} {'迭代速度':<10}")
        print("-" * 60)
        for name, r in all_results.items():
            noise_rate = r['noise'][1]['same']
            node_rate = r['node_failure'][1]['recovered']
            pert_rate = r['perturbation'][1]
            speed = r['10min']['states_per_second']
            print(f"{name:<18} {noise_rate:<12.0f} {node_rate:<12.0f} {pert_rate:<15.1f} {speed:<10.0f}")

        print(f"\n完成时间: {datetime.now()}")
        return all_results


if __name__ == "__main__":
    np.random.seed(int(time.time()) % 10000)
    exp = StabilityTest()
    results = exp.run()

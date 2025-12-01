# ucb_selector.py
import math

class UCBSelector:
    def __init__(self, choices):
        self.choices = choices
        self.counts = {choice: 0 for choice in choices}  # Số lần chọn
        self.rewards = {choice: 0.0 for choice in choices}  # Tổng reward
        self.total_pulls = 0
    
    def select(self, exploration_factor=2.0):
        """
        Chọn choice theo UCB formula:
        UCB(arm) = avg_reward + C * sqrt(ln(total_pulls) / arm_pulls)
        """
        if self.total_pulls < len(self.choices):
            # Giai đoạn đầu: thử tất cả arms ít nhất 1 lần
            for choice in self.choices:
                if self.counts[choice] == 0:
                    return choice
        
        ucb_values = {}
        for choice in self.choices:
            avg_reward = self.rewards[choice] / max(self.counts[choice], 1)
            exploration_bonus = exploration_factor * math.sqrt(
                math.log(self.total_pulls) / max(self.counts[choice], 1)
            )
            ucb_values[choice] = avg_reward + exploration_bonus
        
        # Chọn choice có UCB cao nhất
        return max(ucb_values, key=ucb_values.get)
    
    def update(self, choice, reward):
        """
        Cập nhật reward sau khi nhận feedback
        reward: 1.0 (Prio 1), 0.5 (Prio 2), 0.0 (Prio 3)
        """
        self.counts[choice] += 1
        self.rewards[choice] += reward
        self.total_pulls += 1
    
    def get_best_choice(self):
        """Trả về choice có avg reward cao nhất"""
        avg_rewards = {
            choice: self.rewards[choice] / max(self.counts[choice], 1)
            for choice in self.choices
        }
        return max(avg_rewards, key=avg_rewards.get)
#!/usr/bin/env python3
"""
MONOPOLY-LK LOG VERIFICATION SYSTEM
Comprehensive automated bug detection and analysis
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PlayerState:
    """Tracks player state at each checkpoint"""
    player_id: int
    name: str
    cash: int
    net_worth: int
    properties_owned: int
    hotels: int
    is_bankrupt: bool = False
    outstanding_loan: int = 0
    line_number: int = 0

@dataclass
class Transaction:
    """Records a financial transaction"""
    round_num: int
    line_num: int
    payer: str
    payee: str
    amount: int
    description: str
    payer_before: int = 0
    payer_after: int = 0

@dataclass
class BugFinding:
    """Represents a confirmed or suspected bug"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # Consistency, Ownership, Lifecycle, Ledger, Arithmetic, Bounds, Structure
    claim: str
    evidence_lines: List[int]
    excerpt: str
    confirmed: bool = False
    notes: str = ""

# ============================================================================
# LOG PARSER
# ============================================================================

class MonopolyLogParser:
    def __init__(self, log_path):
        self.log_path = log_path
        self.lines = []
        self.player_states = defaultdict(list)  # player_name -> list of PlayerState
        self.transactions = []
        self.round_summaries = {}  # round_num -> list of PlayerState
        self.bugs = []
        self.board_mapping = {}  # square_index -> square_name
        self.player_names = ["Aggressive Investor", "Conservative Banker", "Risk Taker", "Opportunity Trader"]
        
    def load_log(self):
        """Load and parse the log file"""
        try:
            with open(self.log_path, 'r') as f:
                self.lines = f.readlines()
            print(f"✓ Loaded {len(self.lines)} lines from {self.log_path}")
            return True
        except FileNotFoundError:
            print(f"✗ Log file not found: {self.log_path}")
            return False
    
    def parse_all(self):
        """Execute all parsing and analysis"""
        self._initialize_board_mapping()
        self._parse_round_summaries()
        self._parse_transactions()
        self._analyze_consistency()
        self._analyze_ownership()
        self._analyze_lifecycle()
        self._analyze_ledger()
        self._analyze_arithmetic()
        self._analyze_bounds()
        self._analyze_structure()
    
    def _initialize_board_mapping(self):
        """Build mapping of square names to indices"""
        square_mapping = {
            "GO": 0, "Pettah": 1, "Maradana": 3, "Colombo Fort Railway Station": 5,
            "Bambalapitiya": 6, "Wellawatta": 8, "Mount Lavinia": 9, "Nugegoda": 11,
            "Maharagama": 13, "Kottawa": 14, "Kandy Railway Station": 15,
            "Negombo": 16, "Katunayake": 18, "Ja-Ela": 19, "Kandy City": 21,
            "Peradeniya": 23, "Katugastota": 24, "Galle Railway Station": 25,
            "Galle Fort": 26, "Unawatuna": 27, "National Water Supply and Drainage Board": 28,
            "Hikkaduwa": 29, "Jaffna Town": 31, "Nallur": 32, "Trincomalee": 34,
            "Jaffna Railway Station": 35, "Nuwara Eliya": 37, "Galle Face": 39
        }
        self.board_mapping = square_mapping
    
    def _parse_round_summaries(self):
        """Extract round summaries with player states"""
        current_round = 0
        current_player_states = []
        
        for i, line in enumerate(self.lines):
            # Detect round headers
            if "Round " in line and "Summary" in line:
                match = re.search(r"Round (\d+) Summary", line)
                if match:
                    current_round = int(match.group(1))
                    current_player_states = []
            
            # Parse player data within round summary
            if current_round > 0 and any(pname in line for pname in self.player_names):
                player_name = None
                for pname in self.player_names:
                    if pname in line:
                        player_name = pname
                        break
                
                if player_name:
                    # Extract state from next 5 lines
                    state_block = "\n".join(self.lines[i:min(i+10, len(self.lines))])
                    cash_match = re.search(r"Cash : LKR (\d+)", state_block)
                    net_worth_match = re.search(r"Net Worth : LKR (\d+)", state_block)
                    properties_match = re.search(r"Propertie : (\d+)", state_block)
                    hotels_match = re.search(r"Hotels : (\d+)", state_block)
                    bankrupt_match = re.search(r"has been declared bankrupt", state_block)
                    
                    if cash_match:
                        state = PlayerState(
                            player_id=self.player_names.index(player_name),
                            name=player_name,
                            cash=int(cash_match.group(1)),
                            net_worth=int(net_worth_match.group(1)) if net_worth_match else 0,
                            properties_owned=int(properties_match.group(1)) if properties_match else 0,
                            hotels=int(hotels_match.group(1)) if hotels_match else 0,
                            is_bankrupt=bool(bankrupt_match),
                            line_number=i
                        )
                        self.player_states[player_name].append(state)
                        
                        if current_round not in self.round_summaries:
                            self.round_summaries[current_round] = []
                        self.round_summaries[current_round].append(state)
    
    def _parse_transactions(self):
        """Extract financial transactions"""
        for i, line in enumerate(self.lines):
            # Rent payments
            if "Rent Paid" in line:
                amount_match = re.search(r"LKR (\d+)", line)
                if amount_match:
                    amount = int(amount_match.group(1))
                    # Extract payer and payee from context
                    context = "\n".join(self.lines[max(0, i-2):min(len(self.lines), i+3)])
                    payer_match = re.search(r"(\w+) landed on", context)
                    payee_match = re.search(r"Owner : (.+)\.", context)
                    
                    if payer_match and payee_match:
                        payer = payer_match.group(1)
                        payee = payee_match.group(1).strip()
                        self.transactions.append(Transaction(
                            round_num=0, line_num=i, payer=payer, payee=payee,
                            amount=amount, description="Rent Payment"
                        ))
            
            # Property purchases
            elif "purchased" in line and "LKR" in line:
                match = re.search(r"(\w+) purchased (.+) for LKR (\d+)", line)
                if match:
                    player, property_name, amount = match.groups()
                    self.transactions.append(Transaction(
                        round_num=0, line_num=i, payer=player, payee="Bank",
                        amount=int(amount), description=f"Purchase: {property_name}"
                    ))
            
            # Auction purchases
            elif "wins the auction" in line:
                winner_match = re.search(r"(\w+) wins the auction", line)
                if winner_match:
                    # Find auction amount by looking backward
                    for j in range(max(0, i-20), i):
                        bid_match = re.search(r"bids LKR (\d+)", self.lines[j])
                        if bid_match:
                            amount = int(bid_match.group(1))
                            self.transactions.append(Transaction(
                                round_num=0, line_num=i, payer=winner_match.group(1),
                                payee="Bank", amount=amount, description="Auction Purchase"
                            ))
                            break
    
    def _analyze_consistency(self):
        """CHECK: State-Space Consistency"""
        print("\n" + "="*80)
        print("ANALYSIS 1: STATE-SPACE CONSISTENCY")
        print("="*80)
        
        # Check if player names are consistent
        player_name_variants = defaultdict(set)
        for i, line in enumerate(self.lines):
            for pname in self.player_names:
                if pname in line:
                    player_name_variants[pname].add(pname)
        
        print(f"✓ Player names: {len(player_name_variants)} unique names found")
        for name, variants in player_name_variants.items():
            if len(variants) > 1:
                self.add_bug(BugFinding(
                    severity="HIGH",
                    category="Consistency",
                    claim=f"Player '{name}' has {len(variants)} name variants",
                    evidence_lines=[],
                    excerpt=f"Variants: {variants}",
                    confirmed=True
                ))
        
        # Check board square names are consistent
        square_references = defaultdict(list)
        for i, line in enumerate(self.lines):
            for square_name in self.board_mapping.keys():
                if square_name in line:
                    square_references[square_name].append(i)
        
        print(f"✓ Board squares: {len(square_references)} unique squares referenced")
        
        # Check for constant violations
        for round_num, states in self.round_summaries.items():
            if round_num > 1:  # After round 1, verify property count is monotonic (can only increase)
                prev_states = self.round_summaries.get(round_num - 1, [])
                for curr_state in states:
                    prev_match = next((s for s in prev_states if s.name == curr_state.name), None)
                    if prev_match and curr_state.properties_owned < prev_match.properties_owned and not curr_state.is_bankrupt:
                        self.add_bug(BugFinding(
                            severity="CRITICAL",
                            category="Consistency",
                            claim=f"{curr_state.name} property count decreased from {prev_match.properties_owned} to {curr_state.properties_owned} in round {round_num} without bankruptcy",
                            evidence_lines=[prev_match.line_number, curr_state.line_number],
                            excerpt=f"Round {round_num-1}: {prev_match.properties_owned}, Round {round_num}: {curr_state.properties_owned}",
                            confirmed=True
                        ))
    
    def _analyze_ownership(self):
        """CHECK: Ownership/Assignment Integrity"""
        print("\n" + "="*80)
        print("ANALYSIS 2: OWNERSHIP/ASSIGNMENT INTEGRITY")
        print("="*80)
        
        self_payments = []
        
        for trans in self.transactions:
            # Check for self-payments
            if trans.payer == trans.payee and trans.payee != "Bank":
                self_payments.append(trans)
                self.add_bug(BugFinding(
                    severity="CRITICAL",
                    category="Ownership",
                    claim=f"{trans.payer} paid itself LKR {trans.amount} for {trans.description}",
                    evidence_lines=[trans.line_num],
                    excerpt=f"{trans.payer} -> {trans.payee}: LKR {trans.amount}",
                    confirmed=True
                ))
        
        if not self_payments:
            print("✓ No self-payments detected")
        else:
            print(f"✗ Found {len(self_payments)} self-payment(s)")
        
        # Check rent collected by correct owner
        print(f"✓ Rent transactions analyzed: {len([t for t in self.transactions if 'Rent' in t.description])}")
    
    def _analyze_lifecycle(self):
        """CHECK: Lifecycle/Elimination Handling"""
        print("\n" + "="*80)
        print("ANALYSIS 3: LIFECYCLE/ELIMINATION HANDLING")
        print("="*80)
        
        bankrupt_players = {}
        
        # Find bankruptcy events
        for i, line in enumerate(self.lines):
            if "has been declared bankrupt" in line:
                player_match = re.search(r"(\w+) has been declared bankrupt", line)
                if player_match:
                    player_name = player_match.group(1)
                    bankrupt_players[player_name] = i
                    
                    # Look for preceding cash/asset info
                    context_before = "\n".join(self.lines[max(0, i-5):i])
                    print(f"✓ Bankruptcy event for {player_name} at line {i}")
                    
                    # Check for any actions after bankruptcy
                    for j in range(i+1, min(i+50, len(self.lines))):
                        if f"{player_name}" in self.lines[j] and "paid" in self.lines[j]:
                            self.add_bug(BugFinding(
                                severity="CRITICAL",
                                category="Lifecycle",
                                claim=f"Bankrupt player '{player_name}' performed action after elimination",
                                evidence_lines=[i, j],
                                excerpt=f"Bankruptcy at {i}, Action at {j}: {self.lines[j].strip()}",
                                confirmed=True
                            ))
        
        if not bankrupt_players:
            print("✓ No bankruptcy events found in log (or game still running)")
        else:
            print(f"✓ Bankruptcy events found: {len(bankrupt_players)}")
    
    def _analyze_ledger(self):
        """CHECK: Ledger/Running-Total Spot-Checks"""
        print("\n" + "="*80)
        print("ANALYSIS 4: LEDGER/RUNNING-TOTAL VERIFICATION")
        print("="*80)
        
        discrepancies = []
        
        # For each round, check cash + net worth math
        for round_num in sorted(self.round_summaries.keys()):
            for state in self.round_summaries[round_num]:
                # Basic sanity: net worth >= cash (assets can't be negative)
                if state.net_worth < state.cash:
                    discrepancies.append({
                        'round': round_num,
                        'player': state.name,
                        'issue': f"Net worth ({state.net_worth}) < cash ({state.cash})",
                        'line': state.line_number
                    })
                    self.add_bug(BugFinding(
                        severity="CRITICAL",
                        category="Ledger",
                        claim=f"Round {round_num}: {state.name} net worth ({state.net_worth}) < cash ({state.cash})",
                        evidence_lines=[state.line_number],
                        excerpt=f"Cash: {state.cash}, Net Worth: {state.net_worth}",
                        confirmed=True
                    ))
        
        if not discrepancies:
            print(f"✓ All ledger entries verified: net_worth >= cash for all rounds/players")
        else:
            print(f"✗ Found {len(discrepancies)} discrepancies")
    
    def _analyze_arithmetic(self):
        """CHECK: Final/Summary Arithmetic"""
        print("\n" + "="*80)
        print("ANALYSIS 5: FINAL ARITHMETIC VERIFICATION")
        print("="*80)
        
        # Find game end summary
        for i, line in enumerate(self.lines):
            if "Game Over" in line or "Winner" in line:
                # Extract winner summary
                summary_lines = self.lines[i:min(i+20, len(self.lines))]
                summary_text = "\n".join(summary_lines)
                
                cash_match = re.search(r"Total Cash.*LKR (\d+)", summary_text)
                prop_value_match = re.search(r"Total Property Value.*LKR (\d+)", summary_text)
                loan_match = re.search(r"Outstanding Loan.*LKR (\d+)", summary_text)
                net_worth_match = re.search(r"Net Worth.*LKR (\d+)", summary_text)
                
                if all([cash_match, prop_value_match, net_worth_match]):
                    cash = int(cash_match.group(1))
                    prop_value = int(prop_value_match.group(1))
                    loan = int(loan_match.group(1)) if loan_match else 0
                    net_worth = int(net_worth_match.group(1))
                    
                    # Verify: cash + prop_value - loan = net_worth
                    calculated_net_worth = cash + prop_value - loan
                    
                    if calculated_net_worth != net_worth:
                        self.add_bug(BugFinding(
                            severity="CRITICAL",
                            category="Arithmetic",
                            claim=f"Final net worth arithmetic error: {cash} + {prop_value} - {loan} = {calculated_net_worth}, but reported as {net_worth}",
                            evidence_lines=[i],
                            excerpt=f"Expected: {calculated_net_worth}, Reported: {net_worth}, Diff: {net_worth - calculated_net_worth}",
                            confirmed=True
                        ))
                    else:
                        print(f"✓ Final arithmetic verified: {cash} + {prop_value} - {loan} = {net_worth}")
    
    def _analyze_bounds(self):
        """CHECK: Range/Bounds Sanity"""
        print("\n" + "="*80)
        print("ANALYSIS 6: BOUNDS/RANGE SANITY")
        print("="*80)
        
        dice_rolls = []
        invalid_rolls = []
        
        for i, line in enumerate(self.lines):
            # Parse dice rolls
            match = re.search(r"rolled (\d+)", line)
            if match:
                roll = int(match.group(1))
                dice_rolls.append((roll, i))
                
                # Dice should be 2-12
                if roll < 2 or roll > 12:
                    invalid_rolls.append((roll, i))
                    self.add_bug(BugFinding(
                        severity="CRITICAL",
                        category="Bounds",
                        claim=f"Invalid dice roll: {roll} (must be 2-12)",
                        evidence_lines=[i],
                        excerpt=f"Line {i}: '{line.strip()}'",
                        confirmed=True
                    ))
        
        if not invalid_rolls:
            print(f"✓ All {len(dice_rolls)} dice rolls within valid range [2,12]")
        else:
            print(f"✗ Found {len(invalid_rolls)} invalid dice rolls")
        
        # Check percentages
        for i, line in enumerate(self.lines):
            if "%" in line:
                pct_matches = re.findall(r"(\d+)%", line)
                for pct_str in pct_matches:
                    pct = int(pct_str)
                    if pct < 0 or pct > 100:
                        self.add_bug(BugFinding(
                            severity="HIGH",
                            category="Bounds",
                            claim=f"Invalid percentage: {pct}% at line {i}",
                            evidence_lines=[i],
                            excerpt=line.strip(),
                            confirmed=True
                        ))
    
    def _analyze_structure(self):
        """CHECK: Structural Consistency"""
        print("\n" + "="*80)
        print("ANALYSIS 7: STRUCTURAL CONSISTENCY")
        print("="*80)
        
        # Check for missing round summaries
        round_count = len(self.round_summaries)
        print(f"✓ Found {round_count} round summaries")
        
        # Verify sequential rounds
        for round_num in sorted(self.round_summaries.keys()):
            if round_num > 1:
                if (round_num - 1) not in self.round_summaries:
                    self.add_bug(BugFinding(
                        severity="MEDIUM",
                        category="Structure",
                        claim=f"Round {round_num-1} missing (gap in sequence)",
                        evidence_lines=[],
                        excerpt=f"Rounds found: {sorted(self.round_summaries.keys())}",
                        confirmed=True
                    ))
        
        # Check for inconsistent player count across rounds
        player_counts = defaultdict(set)
        for round_num, states in self.round_summaries.items():
            player_counts[round_num] = len(set(s.name for s in states))
        
        first_round_count = player_counts.get(min(player_counts.keys()), 4)
        for round_num, count in player_counts.items():
            if count != first_round_count and round_num > 1:  # Allow decreasing due to bankruptcy
                if count > first_round_count:
                    self.add_bug(BugFinding(
                        severity="CRITICAL",
                        category="Structure",
                        claim=f"Player count increased from {first_round_count} to {count} at round {round_num}",
                        evidence_lines=[],
                        excerpt=f"Round 1: {first_round_count} players, Round {round_num}: {count} players",
                        confirmed=True
                    ))
    
    def add_bug(self, bug: BugFinding):
        """Register a bug finding"""
        self.bugs.append(bug)
    
    def generate_report(self):
        """Generate comprehensive bug report"""
        print("\n" + "="*80)
        print("FINAL BUG REPORT")
        print("="*80)
        
        critical_bugs = [b for b in self.bugs if b.severity == "CRITICAL"]
        high_bugs = [b for b in self.bugs if b.severity == "HIGH"]
        medium_bugs = [b for b in self.bugs if b.severity == "MEDIUM"]
        
        print(f"\n📊 SUMMARY:")
        print(f"  🔴 CRITICAL: {len(critical_bugs)}")
        print(f"  🟠 HIGH:     {len(high_bugs)}")
        print(f"  🟡 MEDIUM:   {len(medium_bugs)}")
        print(f"  📈 TOTAL:    {len(self.bugs)}")
        
        for severity, bugs in [
            ("🔴 CRITICAL", critical_bugs),
            ("🟠 HIGH", high_bugs),
            ("🟡 MEDIUM", medium_bugs)
        ]:
            if bugs:
                print(f"\n{severity} ISSUES:")
                for i, bug in enumerate(bugs, 1):
                    print(f"\n  [{i}] {bug.category}")
                    print(f"      Claim: {bug.claim}")
                    print(f"      Lines: {bug.evidence_lines}")
                    print(f"      Quote: '{bug.excerpt}'")
                    if bug.notes:
                        print(f"      Notes: {bug.notes}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    log_path = "monopolylog.txt"
    
    parser = MonopolyLogParser(log_path)
    
    if not parser.load_log():
        sys.exit(1)
    
    print("\n" + "="*80)
    print("MONOPOLY-LK LOG VERIFICATION SYSTEM")
    print("="*80)
    
    parser.parse_all()
    parser.generate_report()
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")

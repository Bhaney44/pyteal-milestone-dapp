from pyteal import *
from contract_helpers import contract_events

def approval_program():

    # App Global States
    op_set_state = Bytes("set_state")
    op_accept = Bytes("accept")
    op_decline = Bytes("decline")
    op_submit = Bytes("submit")
    op_withdraw = Bytes("withdraw")
    op_refund = Bytes("refund")

    # App Global Schemas (byteslice | uint64)
    global_creator = Bytes("global_creator") # byteslice [the deployer of the contract address]
    global_start_date = Bytes("start_date") # unint64 [time the milestone is to start]
    global_end_date = Bytes("end_date") # unint64 [time the milestone is to end]
    global_amount = Bytes("amount") # unint64 [amont to be paid in algo for milestone]
    global_altimatum = Bytes("altimatum") # unint64 [time the client has to review submission and accept or decline after freelancer submission]

    global_client = Bytes("client") # byteslice
    global_freelancer = Bytes("freelancer") # byteslice

    global_submission_date = Bytes("submission_date") # unit64 [when the freelancer submitted the work for review]
    global_submitted = Bytes("submit") # byteslice
    global_sent = Bytes("sent") # byteslice [status of payment]


    def initialize_app():
        # This fucntion sets the initialize contract states.
        # It handles the deployment phase of the contract.

        return Seq([
            Assert(Txn.application_args.length() == Int(3)), # making sure we are sending 3 argumnets with the cntract call
            
            # set the states
            App.globalPut(global_creator, Txn.sender()), # we set the global contract deploer to the sender of the transaction
            App.globalPut(global_client, Txn.application_args[0]), # we set the client address
            App.globalPut(global_freelancer, Txn.application_args[1]), # we set the freelancers address
            App.globalPut(global_amount, Txn.amount, Btoi(Txn.application_args[2])), # we set the milestone amount in algo
            App.globalPut(global_altimatum, Int(0)), # set the altimatum to 0
            App.globalPut(global_sent, Bytes("False")), # the paymnet hasn't been made
            App.globalPut(global_submission_date, Int(0)), # No submission date has been set
            App.globalPut(global_submitted, Bytes("False")), # milestone hasn't been submitted yet. 
            App.globalPut(global_start_date, Int(0)), # set the start date to Int(0)
            App.globalPut(global_end_date, Int(0)), # set the end date to Int(0)
            Approve()
        ])


    def delete_app():
        # send all algo the client address
        # set all global variables to initial state
        pass

    @Subroutine(TealType.none)
    def set_state():
        # This fucntion sets the parameters to get the contract started
        # It is a grouped transaction with the second being a payment transaction to the smart contract escrow address.

        return Seq([
            # Run some checks
            Assert(
                And(
                    Global.group_size() == Int(2), # assert it a group transaction with a group size of 2
                    Txn.group_index() == Int(0),
                    Txn.sender() == App.globalGet(global_client), # assert it is the client making this call
                    Txn.application_args.length() == Int(3), # assert the length of the argumnets passed is 3

                    Gtxn[1].type_enum() == TxnType.Payment, # assert the second transaction in the group is a payment transaction
                    Gtxn[1].amount() == App.globalGet(global_amount), # assert the right amount is sent
                    Gtxn[1].receiver() == Global.current_application_address(), # assert the payment is to the smart contract escrow address
                    Gtxn[1].close_to_receiver() == Global.zero_address(),
                    App.globalGet(global_start_date) == App.globalGet(global_end_date) == Int(0), # assert the contract hasn't started
                )
            ),

            #  set the start and end dates
            App.globalPut(global_start_date, Btoi(Txn.application_args[1])),
            App.globalPut(global_end_date, Btoi(Txn.application_args[2])),
            Approve()
        ])

    @Subroutine(TealType.none)
    def submit():
        return Seq([
            Assert(
                And(
                    Txn.sender() == App.globalGet(global_freelancer), # the transaction sender must be the freelancer associated with the contract
                    App.globalGet(global_start_date) != Int(0), # assert that the milestone has started and been set
                    App.globalGet(global_end_date) != Int(0),
                    App.globalGet(global_submitted) == Bytes("False"), # assert that the submission has not beem previously made
                    App.globalGet(global_sent) == Bytes("False"), # assert that the payment hasn't beem made
                    Txn.application_args[1] == Bytes("True"), # assert that the second argumnet equals True to set submission status
                    Txn.application_args.length() == Int(2),

                    App.globalGet(global_start_date < Global.latest_timestamp()), # assert the start date is less than current date time
                    App.globalGet(global_end_date >= Global.latest_timestamp()), # assert that the enddate is greater than the current date time
                
                )
            ),
            App.globalPut(global_submitted, Txn.application_args[1]), # we set the submission status to true
            App.globalPut(global_submission_date, Global.latest_timestamp()), # we set the submission date
            # check here -->
            App.globalPut(global_altimatum, Global.latest_timestamp() + Int(7)), # we set the altimatum date (7 days)
            Approve()
        ])

    @Subroutine(TealType.none)
    def accept():
        # case of client accpeting the milestone
        pass

    @Subroutine()
    def decline():
        pass

    @Subroutine(TealType.none)
    def refund():
        # client request for refund when
        # 1. work has not began
        # 2. work has eneded and freelancer didn't submit
        pass

    @Subroutine(TealType.none)
    def withdraw():
        # case client hasn't accepted or declined submission
        # altimatum time must have beem exceeded
        # freelancer must have submitted work
        # payment hasn't been made by client
        pass

    @Subroutine(TealType.none)
    def sendPayment(receiver, amount_in_algo, close_to_receiver):
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment, # specifies the type of transacion been made (paymnet, application_call, etc)
                TxnField.amount: amount_in_algo - (Global.min_txn_fee() + Global.min_balance()), # we subtract the cost for making the call (gas fee) and the minimum amount of algo that must be in an algorand account
                TxnField.sender: Global.current_application_address(), # The sender of this payment is the smart contract escrow address
                TxnField.receiver: receiver, # Funds receiver
                TxnField.close_remainder_to: close_to_receiver # address to send the remaining algo in the escrow account to
            }),
            InnerTxnBuilder.Submit()
        ])

    return contract_events(
        delete_contract=delete_app(),
        initialize_contract=initialize_app(),
        no_op_contract=Seq([
            Cond(
                [Txn.application_args[0] == op_set_state, set_state()],
                [Txn.application_args[0] == op_submit, submit()],
                [Txn.application_args[0] == op_accept, accept()],
                [Txn.application_args[0] == op_decline, decline()],
                [Txn.application_args[0] == op_refund, refund()]
                [Txn.application_args[0] == op_withdraw, withdraw()],
            ),
            Reject()
        ])
    )

def clear_program():
    return Approve()
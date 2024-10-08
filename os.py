import streamlit as st
from collections import deque
import pandas as pd
import csv
import os

# Define the Order class with priority levels
class Order:
    def __init__(self, order_id, customer_name, order_type, preparation_time, station, priority=0):
        self.order_id = order_id
        self.customer_name = customer_name
        self.order_type = order_type  # e.g., dine-in, takeaway, online
        self.preparation_time = preparation_time  # time in minutes
        self.station = station  # kitchen station (e.g., grill, fryers)
        self.priority = priority  # Priority: 0 = low, 1 = medium, 2 = high
        self.wait_time = 0
        self.turnaround_time = 0
        self.completion_time = 0
        self.arrival_time = 0

    def __str__(self):
        return f"Order {self.order_id} for {self.customer_name} ({self.order_type}, {self.station}, Priority: {self.priority}): {self.preparation_time} min left"


# FCFS (First Come First Serve) Scheduler
def fcfs_scheduler(orders):
    completed_orders = []
    current_time = 0
    for order in orders:
        order.arrival_time = current_time
        order.completion_time = current_time + order.preparation_time
        order.wait_time = order.arrival_time  # Assuming all orders arrive at the same time
        order.turnaround_time = order.completion_time - order.arrival_time
        current_time += order.preparation_time
        completed_orders.append(order)
    return completed_orders


# Priority Scheduling (higher priority = processed first)
def priority_scheduler(orders):
    completed_orders = []
    current_time = 0
    sorted_orders = sorted(orders, key=lambda o: o.priority, reverse=True)
    for order in sorted_orders:
        order.arrival_time = current_time
        order.completion_time = current_time + order.preparation_time
        order.wait_time = order.arrival_time  # Assuming all orders arrive at the same time
        order.turnaround_time = order.completion_time - order.arrival_time
        current_time += order.preparation_time
        completed_orders.append(order)
    return completed_orders


# Enhanced Round Robin Scheduling function
def enhanced_round_robin_scheduling(orders, time_slice, peak_hour=False):
    order_queue = deque(orders)
    completed_orders = []
    current_time = 0
    station_loads = {}

    # Initialize station load counts
    for order in orders:
        if order.station not in station_loads:
            station_loads[order.station] = 0

    # Peak hour handling
    if peak_hour:
        time_slice *= 2

    while order_queue:
        current_order = order_queue.popleft()
        station_loads[current_order.station] += 1
        current_order.arrival_time = current_time

        if current_order.preparation_time > time_slice:
            current_order.preparation_time -= time_slice
            current_time += time_slice
            order_queue.append(current_order)
        else:
            current_time += current_order.preparation_time
            current_order.completion_time = current_time
            current_order.wait_time = current_order.arrival_time  # Assuming all orders arrive at the same time
            current_order.turnaround_time = current_order.completion_time - current_order.arrival_time
            completed_orders.append(current_order)

    return completed_orders, station_loads


# Function to save orders to a CSV file
def save_orders_to_csv(orders):
    with open("orders.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Order ID", "Customer Name", "Order Type", "Preparation Time", "Station", "Priority", 
                         "Arrival Time", "Completion Time", "Wait Time", "Turnaround Time"])
        for order in orders:
            writer.writerow([order.order_id, order.customer_name, order.order_type, order.preparation_time, 
                             order.station, order.priority, order.arrival_time, order.completion_time, 
                             order.wait_time, order.turnaround_time])


# Function to load orders from CSV file with error handling
def load_orders_from_csv():
    orders = []
    if os.path.exists("orders.csv"):
        try:
            with open("orders.csv", mode="r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    orders.append(Order(
                        order_id=row.get("Order ID"),
                        customer_name=row.get("Customer Name"),
                        order_type=row.get("Order Type"),
                        preparation_time=int(row.get("Preparation Time", 0)),
                        station=row.get("Station"),
                        priority=int(row.get("Priority", 0))
                    ))
                    # Assign loaded metrics
                    orders[-1].arrival_time = int(row.get("Arrival Time", 0))
                    orders[-1].completion_time = int(row.get("Completion Time", 0))
                    orders[-1].wait_time = int(row.get("Wait Time", 0))
                    orders[-1].turnaround_time = int(row.get("Turnaround Time", 0))
        except Exception as e:
            st.error(f"Error loading orders: {e}")
    else:
        st.warning("No orders found. Please add some orders first.")
    return orders


# Streamlit App
def streamlit_app():
    st.title("Automated Restaurant Order Scheduling")

    # Input form for adding orders
    st.header("Add New Orders")
    order_id = st.text_input("Order ID")
    customer_name = st.text_input("Customer Name")
    order_type = st.selectbox("Order Type", ["dine-in", "takeaway", "online"])
    preparation_time = st.number_input("Preparation Time (minutes)", min_value=1)
    station = st.selectbox("Kitchen Station", ["Grill", "Fryers", "Oven", "Salads"])
    priority = st.selectbox("Order Priority", [0, 1, 2])  # 0 = low, 1 = medium, 2 = high

    if st.button("Add Order"):
        new_order = Order(order_id, customer_name, order_type, preparation_time, station, priority)
        orders = load_orders_from_csv()
        orders.append(new_order)
        save_orders_to_csv(orders)
        st.success(f"Order {order_id} added successfully!")

    # Display current orders
    st.header("Current Orders")
    orders = load_orders_from_csv()
    if orders:
        df_orders = pd.DataFrame([(o.order_id, o.customer_name, o.order_type, o.preparation_time, 
                                   o.station, o.priority, o.arrival_time, o.completion_time,
                                   o.wait_time, o.turnaround_time)
                                  for o in orders],
                                 columns=["Order ID", "Customer Name", "Order Type", "Preparation Time", 
                                          "Station", "Priority", "Arrival Time", "Completion Time", 
                                          "Wait Time", "Turnaround Time"])
        st.write(df_orders)

    # Automatic Scheduling Decision
    st.header("Automatic Order Processing")
    time_slice = st.number_input("Time Slice (for Round Robin)", min_value=1, value=5)
    peak_hour = st.checkbox("Is it peak hour?", value=False)

    if st.button("Start Scheduling"):
        completed_orders = []

        # Determine the scheduling method based on order characteristics
        if any(order.priority == 2 for order in orders):  # Check for high-priority orders
            st.write("Using Priority Scheduling due to high-priority orders.")
            completed_orders = priority_scheduler(orders)
        elif all(order.priority <= 1 for order in orders):  # All orders normal or low priority
            st.write("Using FCFS Scheduling as all orders have normal priority.")
            completed_orders = fcfs_scheduler(orders)
        else:
            st.write("Using Round Robin Scheduling to balance the workload.")
            completed_orders, station_loads = enhanced_round_robin_scheduling(orders, time_slice, peak_hour)
            st.subheader("Station Load Balancing Results")
            st.write(station_loads)

        save_orders_to_csv(completed_orders)

        # Show completed orders
        st.subheader("Completed Orders")
        df_completed = pd.DataFrame([(o.order_id, o.customer_name, o.order_type, o.preparation_time, 
                                       o.station, o.priority, o.arrival_time, o.completion_time,
                                       o.wait_time, o.turnaround_time)
                                     for o in completed_orders],
                                    columns=["Order ID", "Customer Name", "Order Type", "Preparation Time", 
                                             "Station", "Priority", "Arrival Time", "Completion Time", 
                                             "Wait Time", "Turnaround Time"])
        st.write(df_completed)

# Run the Streamlit app
if __name__ == "__main__":
    streamlit_app()

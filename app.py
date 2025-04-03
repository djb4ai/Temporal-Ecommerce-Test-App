from aiohttp import web
import aiohttp_jinja2
import jinja2
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from temporalio.client import Client
import asyncio
import json
from workflows.order_workflow import OrderProcessingWorkflow, OrderRequest
from workflows.rewards_workflow import CustomerRewardsWorkflow

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def json_response(data, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    })
    return web.json_response(data, headers=headers, dumps=lambda x: json.dumps(x, cls=DateTimeEncoder), **kwargs)

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = mongo_client['ecommerce_db']

# Collections
orders = db['orders']
inventory = db['inventory']
rewards = db['rewards']
balances = db['balances']

# Temporal client setup
temporal_client = None

async def get_temporal_client():
    global temporal_client
    if temporal_client is None:
        try:
            temporal_client = await Client.connect("localhost:7233")
            print("Successfully connected to Temporal server")
        except Exception as e:
            print(f"Failed to connect to Temporal server: {str(e)}")
            print("Please ensure Temporal server is running on localhost:7233")
            print("You can start it using: docker run -d -p 7233:7233 -p 7234:7234 -p 7235:7235 temporalio/auto-setup:1.20")
            raise
    return temporal_client

# Routes
@aiohttp_jinja2.template('index.html')
async def index(request):
    return {}

async def get_inventory_handler(request):
    items = list(inventory.find({}, {'_id': 0}))
    return json_response(items)

async def get_orders_handler(request):
    orders_list = list(orders.find({}, {'_id': 0}))
    return json_response(orders_list)

async def get_balance_handler(request):
    try:
        # For demo purposes, using a default user ID
        user_id = "default_user"
        
        # Get balance from MongoDB
        balance_doc = balances.find_one({'user_id': user_id})
        
        if not balance_doc:
            return json_response({
                'error': 'No balance found. Please initialize the database.',
                'balance': 0.0,
                'transactions': []
            }, status=404)
        
        # Get transaction history
        transactions = balance_doc.get('transactions', [])
        
        return json_response({
            'balance': balance_doc.get('balance', 0.0),
            'transactions': transactions[-5:] if transactions else []  # Return last 5 transactions
        })
    except Exception as e:
        print(f"Error fetching balance: {str(e)}")
        return json_response({
            'error': str(e),
            'balance': 0.0,
            'transactions': []
        }, status=500)

async def get_rewards_handler(request):
    try:
        # For demo purposes, using a default user ID
        user_id = "default_user"
        
        # Get rewards from MongoDB
        #user_rewards = rewards.find_one({'user_id': user_id})

        # Instead of getting the rewards from MongoDB, I will get it from the rewards workflow
        # Get the rewards from the rewards workflow
        # rewards_workflow = CustomerRewardsWorkflow()
        # rewards_workflow.run(user_id)
        # using the get_status query

        client = await get_temporal_client()
        handle = client.get_workflow_handle_for(CustomerRewardsWorkflow.run, "rewards_"+user_id)  
        results = await handle.query(CustomerRewardsWorkflow.get_status)  
        
        if results:
            total_points = results.get('points', 0)
            #total_points = user_rewards.get('total_points', 0)
            
            # Calculate tier based on points
            if total_points >= 1000:
                tier = "platinum"
            elif total_points >= 500:
                tier = "gold"
            elif total_points >= 100:
                tier = "silver"
            else:
                tier = "basic"
                
            return json_response({
                'points': total_points,
                'tier': tier
            })
        else:
            return json_response({
                'points': 0,
                'tier': 'basic'
            })
    except Exception as e:
        print(f"Error fetching rewards: {str(e)}")
        return json_response({
            'error': str(e),
            'points': 0,
            'tier': 'basic'
        }, status=500)

async def place_order(request):
    try:
        data = await request.json()
        if not data or 'items' not in data:
            return json_response({'error': 'Invalid request data'}, status=400)

        items = data['items']
        
        # Create order record
        order = {
            'items': items,
            'status': 'initiated',
            'total': sum(item['price'] * item['quantity'] for item in items),
            'created_at': datetime.utcnow()
        }
        result = orders.insert_one(order)
        order_id = str(result.inserted_id)
        
        # Update order with the order_id for easier reference
        orders.update_one(
            {'_id': result.inserted_id},
            {'$set': {'order_id': order_id}}
        )
        
        # Start order processing workflow
        try:
            client = await get_temporal_client()
            workflow_id = f"order_{order_id}"
            await client.start_workflow(
                OrderProcessingWorkflow,
                OrderRequest(
                    user_id="default_user",
                    order_id=order_id,
                    items=items
                ),
                id=workflow_id,
                task_queue="ecommerce-task-queue",
            )
        except Exception as e:
            print(f"Failed to start workflow: {str(e)}")
            # Still return success as order is created
            pass
        
        return json_response({
            'message': 'Order placed successfully', 
            'order_id': order_id,
            'workflow_id': f"order_{order_id}"
        })
    except Exception as e:
        print(f"Error placing order: {str(e)}")
        return json_response({'error': str(e)}, status=500)

async def simulate_failure(request):
    try:
        data = await request.json()
        if not data or 'type' not in data or 'workflow_id' not in data:
            return json_response({'error': 'Invalid request data'}, status=400)
            
        failure_type = data['type']
        workflow_id = data['workflow_id']
        
        # Simulate failure based on type
        # This would be implemented based on your failure simulation needs
        return json_response({'message': f'Simulated {failure_type} failure for workflow {workflow_id}'})
    except Exception as e:
        print(f"Error simulating failure: {str(e)}")
        return json_response({'error': str(e)}, status=500)

async def init_app():
    app = web.Application()
    
    # Setup Jinja2 templates
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('templates')
    )
    
    # Add CORS middleware
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == 'OPTIONS':
                return web.Response(
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
                )
            response = await handler(request)
            return response
        return middleware

    app.middlewares.append(cors_middleware)
    
    # Add routes
    app.router.add_get('/', index)
    app.router.add_get('/inventory', get_inventory_handler)
    app.router.add_get('/orders', get_orders_handler)
    app.router.add_get('/rewards', get_rewards_handler)
    app.router.add_get('/balance', get_balance_handler)
    app.router.add_post('/order', place_order)
    app.router.add_post('/simulate_failure', simulate_failure)
    
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app())
    web.run_app(app, port=5000)
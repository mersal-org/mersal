Routing
=======

..
   .. _routing:

   .. note::
      This page is a placeholder for routing documentation. It will be expanded in future updates.

   Message Routing in Mersal
   ------------------------

   Routing in Mersal determines where messages should be sent based on their type. The default router uses a configuration that maps message types to queue addresses.

   Basic Configuration
   -----------------

   .. code-block:: python

       from mersal.routing.default import DefaultRouterRegistrationConfig

       # Configure routing for different message types
       router_config = DefaultRouterRegistrationConfig({
           "orders-queue": [OrderCommand, CancelOrderCommand],
           "inventory-queue": [UpdateInventoryCommand],
           "shipping-queue": [ShipOrderCommand]
       })

       # Use the router configuration when creating the app
       plugins = [
           InMemoryTransportPluginConfig(network, "my-app-queue").plugin,
           router_config.plugin
       ]
       app = Mersal("my-app", activator, plugins=plugins)

   With this configuration, messages of type ``OrderCommand`` and ``CancelOrderCommand`` will be sent to the "orders-queue", while messages of other types will go to their respective queues.

   More details on message routing will be added in future documentation updates.

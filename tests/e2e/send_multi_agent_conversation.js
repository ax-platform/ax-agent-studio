#!/usr/bin/env node
/**
 * Send multi-agent conversation messages for context awareness test
 *
 * Simulates a 4-agent conversation:
 * - Agent A (lunar_ray_510) reports performance issues (2 messages)
 * - Agent B (lunar_craft_128) reports related errors (2 messages)
 * - Coordinator (orion_344) asks Observer (ghost_ray_363) to diagnose (1 message)
 */

import { MCPClientManager } from '@mcpjam/sdk';

const CONVERSATION = [
  {
    agent: 'lunar_ray_510',
    message: 'Message 1: I am seeing performance issues in the system',
    description: 'performance issues'
  },
  {
    agent: 'lunar_ray_510',
    message: 'Message 2: CPU usage is at 90% and climbing',
    description: 'CPU at 90%'
  },
  {
    agent: 'lunar_craft_128',
    message: 'Message 3: I am getting timeout errors from the API',
    description: 'timeout errors'
  },
  {
    agent: 'lunar_craft_128',
    message: 'Message 4: Database response time has increased to 5 seconds',
    description: 'slow database'
  },
  {
    agent: 'orion_344',
    message: '@ghost_ray_363 Can you diagnose what is causing these issues?',
    description: 'diagnosis request to @ghost_ray_363'
  }
];

const mcpConfig = {
  lunar_ray_510: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/lunar_ray_510',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  lunar_craft_128: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/lunar_craft_128',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  orion_344: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/orion_344',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

(async () => {
  try {
    console.log('Simulating multi-agent conversation...');

    const manager = new MCPClientManager(mcpConfig, {
      defaultClientName: 'Multi-Agent Context Test',
      defaultClientVersion: '1.0.0'
    });

    for (let i = 0; i < CONVERSATION.length; i++) {
      const { agent, message, description } = CONVERSATION[i];

      await manager.executeTool(agent, 'messages', {
        action: 'send',
        content: message
      });

      console.log(`  ✓ ${agent}: Message ${i + 1} (${description})`);

      // Small delay between messages
      if (i < CONVERSATION.length - 1) {
        await new Promise(r => setTimeout(r, 200));
      }
    }

    console.log('All 5 messages sent successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
})();

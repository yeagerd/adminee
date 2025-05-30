'use client';

import React, { useState } from 'react';
import { mockTasks } from '@/lib/mockData';
import { Task } from '@/lib/types';

const TaskManager: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>(mockTasks);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  const handleAddTask = () => {
    if (newTaskTitle.trim() === '') return;
    const newTask: Task = {
      id: `task-${Date.now()}`,
      title: newTaskTitle,
      completed: false,
      priority: 'medium',
      source: 'user',
    };
    setTasks([...tasks, newTask]);
    setNewTaskTitle('');
  };

  const handleToggleComplete = (taskId: string) => {
    setTasks(
      tasks.map(task =>
        task.id === taskId ? { ...task, completed: !task.completed } : task
      )
    );
  };

  const handleDeleteTask = (taskId: string) => {
    setTasks(tasks.filter(task => task.id !== taskId));
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-3">Tasks</h2>
      <div className="flex mb-3">
        <input
          type="text"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          placeholder="Add a new task"
          className="flex-grow p-2 border rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleAddTask}
          className="px-4 py-2 bg-blue-500 text-white rounded-r hover:bg-blue-600 focus:outline-none"
        >
          Add Task
        </button>
      </div>
      <ul>
        {tasks.map(task => (
          <li key={task.id} className="flex items-center justify-between p-2 mb-1 border-b last:border-b-0">
            <span
              onClick={() => handleToggleComplete(task.id)}
              className={`cursor-pointer ${task.completed ? 'line-through text-gray-500' : ''}`}
            >
              {task.title}
            </span>
            <button
              onClick={() => handleDeleteTask(task.id)}
              className="text-red-500 hover:text-red-700 text-sm"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
      {tasks.length === 0 && <p className="text-gray-500 italic">No tasks yet. Add one above!</p>}
    </div>
  );
};

export default TaskManager; 
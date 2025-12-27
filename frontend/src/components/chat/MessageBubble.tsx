interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

export default function MessageBubble({ role, content, timestamp }: MessageBubbleProps) {
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-2xl ${role === 'user' ? 'order-2' : 'order-1'}`}>
        <div className={`px-4 py-3 rounded-lg ${
          role === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-700'
        }`}>
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
        {timestamp && (
          <p className={`text-xs mt-1 ${
            role === 'user' ? 'text-right text-gray-500' : 'text-gray-500'
          }`}>
            {timestamp.toLocaleTimeString()}
          </p>
        )}
      </div>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
        role === 'user' 
          ? 'bg-blue-600 text-white order-1 ml-2'
          : 'bg-gray-300 order-2 mr-2'
      }`}>
        {role === 'user' ? 'U' : 'AI'}
      </div>
    </div>
  );
}


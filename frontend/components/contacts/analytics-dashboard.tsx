import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, ExternalLink, FileText, Mail, RefreshCw, TrendingDown, TrendingUp, Users, X } from 'lucide-react';
import type { Contact } from '@/types/api/contacts';
import React, { useState } from 'react';

interface ContactAnalyticsProps {
  onClose: () => void;
  contacts: Contact[];
}

interface AnalyticsData {
  totalContacts: number;
  newThisMonth: number;
  growthRate: number;
  sourceDistribution: Record<string, number>;
  relevanceDistribution: {
    high: number;
    medium: number;
    low: number;
  };
  topTags: Array<{ tag: string; count: number }>;
  monthlyGrowth: Array<{ month: string; count: number }>;
  sourceTrends: Record<string, Array<{ month: string; count: number }>>;
}

const ContactAnalyticsDashboard: React.FC<ContactAnalyticsProps> = ({ onClose, contacts }) => {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Calculate analytics data from contacts
  const calculateAnalytics = (): AnalyticsData => {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const totalContacts = contacts.length;
    const newThisMonth = contacts.filter(c => new Date(c.created_at) >= thirtyDaysAgo).length;
    const growthRate = totalContacts > 0 ? (newThisMonth / totalContacts) * 100 : 0;

    // Source distribution
    const sourceDistribution: Record<string, number> = {};
    contacts.forEach(contact => {
      contact.source_services?.forEach(service => {
        sourceDistribution[service] = (sourceDistribution[service] || 0) + 1;
      });
    });

    // Relevance distribution
    const relevanceDistribution = {
      high: contacts.filter(c => (c.relevance_score || 0) >= 0.7).length,
      medium: contacts.filter(c => (c.relevance_score || 0) >= 0.4 && (c.relevance_score || 0) < 0.7).length,
      low: contacts.filter(c => (c.relevance_score || 0) < 0.4).length,
    };

    // Top tags
    const tagCounts: Record<string, number> = {};
    contacts.forEach(contact => {
      contact.tags?.forEach(tag => {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      });
    });
    const topTags = Object.entries(tagCounts)
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Monthly growth (simplified)
    const monthlyGrowth = [
      { month: 'Oct', count: Math.floor(totalContacts * 0.7) },
      { month: 'Nov', count: Math.floor(totalContacts * 0.8) },
      { month: 'Dec', count: Math.floor(totalContacts * 0.9) },
      { month: 'Jan', count: totalContacts },
    ];

    // Source trends (simplified)
    const sourceTrends: Record<string, Array<{ month: string; count: number }>> = {};
    Object.keys(sourceDistribution).forEach(source => {
      sourceTrends[source] = [
        { month: 'Oct', count: Math.floor((sourceDistribution[source] || 0) * 0.6) },
        { month: 'Nov', count: Math.floor((sourceDistribution[source] || 0) * 0.8) },
        { month: 'Dec', count: Math.floor((sourceDistribution[source] || 0) * 0.9) },
        { month: 'Jan', count: sourceDistribution[source] || 0 },
      ];
    });

    return {
      totalContacts,
      newThisMonth,
      growthRate,
      sourceDistribution,
      relevanceDistribution,
      topTags,
      monthlyGrowth,
      sourceTrends,
    };
  };

  const analytics = calculateAnalytics();

  const getSourceServiceIcon = (service: string) => {
    switch (service) {
      case 'office':
        return <ExternalLink className="w-4 h-4" />;
      case 'email':
        return <Mail className="w-4 h-4" />;
      case 'calendar':
        return <Calendar className="w-4 h-4" />;
      case 'documents':
        return <FileText className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getSourceServiceColor = (service: string) => {
    switch (service) {
      case 'office':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'email':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'calendar':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'documents':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate refresh
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsRefreshing(false);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Contact Analytics Dashboard</h2>
        <div className="flex items-center gap-3">
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex items-center gap-2 mb-6">
        <span className="text-sm font-medium text-gray-700">Time Range:</span>
        {(['7d', '30d', '90d', '1y'] as const).map((range) => (
          <Button
            key={range}
            variant={timeRange === range ? "default" : "outline"}
            size="sm"
            onClick={() => setTimeRange(range)}
          >
            {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : range === '90d' ? '90 Days' : '1 Year'}
          </Button>
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-blue-600" />
            <div>
              <p className="text-sm font-medium text-blue-600">Total Contacts</p>
              <p className="text-2xl font-bold text-blue-900">{analytics.totalContacts.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-green-50 rounded-lg p-6 border border-green-200">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-600">New This Month</p>
              <p className="text-2xl font-bold text-green-900">{analytics.newThisMonth.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-purple-50 rounded-lg p-6 border border-purple-200">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-purple-600" />
            <div>
              <p className="text-sm font-medium text-purple-600">Growth Rate</p>
              <p className="text-2xl font-bold text-purple-900">{analytics.growthRate.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        <div className="bg-orange-50 rounded-lg p-6 border border-orange-200">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-orange-600" />
            <div>
              <p className="text-sm font-medium text-orange-600">Active Sources</p>
              <p className="text-2xl font-bold text-orange-900">{Object.keys(analytics.sourceDistribution).length}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Source Distribution */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Source Distribution</h3>
          <div className="space-y-3">
            {Object.entries(analytics.sourceDistribution).map(([source, count]) => {
              const percentage = (count / analytics.totalContacts) * 100;
              return (
                <div key={source} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getSourceServiceIcon(source)}
                    <span className="font-medium capitalize">{source}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600 min-w-[3rem] text-right">
                      {count.toLocaleString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Relevance Distribution */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Relevance Score Distribution</h3>
          <div className="space-y-4">
            {Object.entries(analytics.relevanceDistribution).map(([level, count]) => {
              const percentage = (count / analytics.totalContacts) * 100;
              const color = level === 'high' ? 'bg-green-500' : level === 'medium' ? 'bg-yellow-500' : 'bg-red-500';
              const label = level === 'high' ? 'High (≥70%)' : level === 'medium' ? 'Medium (40-69%)' : 'Low (<40%)';
              
              return (
                <div key={level} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium capitalize">{label}</span>
                    <span className="text-gray-600">{count.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`${color} h-3 rounded-full transition-all duration-300`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Monthly Growth Chart */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Growth</h3>
          <div className="space-y-3">
            {analytics.monthlyGrowth.map((item, index) => {
              const prevCount = index > 0 ? analytics.monthlyGrowth[index - 1].count : 0;
              const growth = prevCount > 0 ? ((item.count - prevCount) / prevCount) * 100 : 0;
              
              return (
                <div key={item.month} className="flex items-center justify-between">
                  <span className="font-medium">{item.month}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-600">{item.count.toLocaleString()}</span>
                    {index > 0 && (
                      <div className={`flex items-center gap-1 text-xs ${
                        growth >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {growth >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(growth).toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top Tags */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Tags</h3>
          <div className="space-y-3">
            {analytics.topTags.map(({ tag, count }) => (
              <div key={tag} className="flex items-center justify-between">
                <Badge variant="secondary">{tag}</Badge>
                <span className="text-sm text-gray-600">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Source Trends */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Source Trends Over Time</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(analytics.sourceTrends).map(([source, trends]) => (
            <div key={source} className="bg-white rounded-lg p-4 border">
              <div className="flex items-center gap-2 mb-3">
                {getSourceServiceIcon(source)}
                <span className="font-medium capitalize">{source}</span>
              </div>
              <div className="space-y-2">
                {trends.map((item, index) => {
                  const prevCount = index > 0 ? trends[index - 1].count : 0;
                  const growth = prevCount > 0 ? ((item.count - prevCount) / prevCount) * 100 : 0;
                  
                  return (
                    <div key={item.month} className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">{item.month}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.count}</span>
                        {index > 0 && (
                          <div className={`flex items-center gap-1 text-xs ${
                            growth >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {growth >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {Math.abs(growth).toFixed(0)}%
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Insights */}
      <div className="mt-8 bg-blue-50 rounded-lg p-6 border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-4">Key Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span className="text-blue-900">
                <strong>Growth:</strong> Contact base grew by {analytics.growthRate.toFixed(1)}% this month
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <span className="text-blue-900">
                <strong>Diversity:</strong> Contacts are spread across {Object.keys(analytics.sourceDistribution).length} sources
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-blue-600" />
              <span className="text-blue-900">
                <strong>Engagement:</strong> {analytics.relevanceDistribution.high} contacts have high relevance scores
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-blue-600" />
              <span className="text-blue-900">
                <strong>Activity:</strong> Most active source is {Object.entries(analytics.sourceDistribution).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-end gap-3 pt-6 border-t border-gray-200 mt-8">
        <Button
          onClick={onClose}
          variant="outline"
        >
          Close
        </Button>
        
        <Button
          onClick={() => {
            // Export analytics data
            console.log('Exporting analytics data...');
          }}
        >
          Export Data
        </Button>
      </div>
    </div>
  );
};

export default ContactAnalyticsDashboard;

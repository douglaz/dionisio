class Recommender 
  class << self                

    def pearson_correlation(x,y)
      intersection = x.rated_products & y.rated_products
      n = intersection.length
      return 0.0 if n == 0

      sum_x = sum_y = sum_x_sq = sum_y_sq = p_sum = 0.0                  

      ratings = Rating.find(:all, :conditions => {:user_id => [x,y], :product_id => intersection})
      product_ratings = ratings.inject({}) do |result,rating| 
        result[rating.product_id] ||= {}  
        result[rating.product_id][rating.user_id] = rating.stars.to_f                         
        result
      end
      product_ratings.values.each do |rate|
        sum_x += rate[x.id]
        sum_y += rate[y.id]
        sum_x_sq += (rate[x.id])**2
        sum_y_sq += (rate[y.id])**2
        p_sum += rate[x.id] * rate[y.id] 
      end

      num = p_sum - ((sum_x*sum_y)/n)
      den = Math.sqrt((sum_x_sq - (sum_x ** 2)/n)*(sum_y_sq - (sum_y ** 2)/n))
      return 0.0 if den == 0.0
      num/den
    end
    alias sim_pearson pearson_correlation

    def sim_distance(item_1,item_2) 
      item_1_id = Product === item_1 ? item_1.id : item_1
      item_2_id = Product === item_2 ? item_2.id : item_2
      
      ratings = Rating.find(:all, :conditions => {:product_id => [item_1_id,item_2_id]})
      n = ratings.length
      return 0.0 if n == 0

      ratings_map = ratings.inject({}) do |result,rating|
        result[rating.user_id] ||= {}  
        result[rating.user_id][rating.product_id] = rating.stars.to_f 
        result
      end
       

      sum_of_squares = ratings_map.values.sum do |map|
        if map.length == 2
          (map[item_1_id]-map[item_2_id])**2
        else
          0
        end
      end                                 
      1.0/(1.0+sum_of_squares)
    end

  end                                    

  module ProfileBased 

    def self.similar_users(user,options = {})
      defaults = { :min_similarity => 0.0}
      options = defaults.merge(options)
      similar_users = []
      User.all.each do |other|
        next if other == user
        similarity = Recommender.pearson_correlation(user,other)
        next if similarity <= options[:min_similarity]
        similar_users << other
        yield other,similarity if block_given?
      end                     
      similar_users
    end

    def self.recommendations_for(user,options = {})
      defaults = {:limit => 8}
      options = defaults.merge options

      totals  = {}
      totals.default= 0.0
      similarity_sum = {}
      similarity_sum.default= 0.0

      self.similar_users(user) do |other,similarity|                         
        # Isso me parace um workarround de um bug do rails!                        
        ids = user.rated_product_ids.empty? ? false  : user.rated_product_ids
        ratings = Rating.find :all, :conditions => ['user_id = ? and product_id NOT IN (?)',other,ids]
        ratings.each do |rating|
          totals[rating.product_id] += (rating.stars.to_f * similarity)
          similarity_sum[rating.product_id] += similarity
        end
      end
      rankings = {}
      totals.each_pair do |product_id,total|
        recommendation_score =  (total/similarity_sum[product_id])
        rankings[product_id] =  recommendation_score
      end      
      ids = rankings.sort{|x,y| y.second <=> x.second }.map(&:first) [0,options[:limit]]
      
      predicted_ratings = rankings.select{ |k,v| ids.include?(k) }
      predicted_ratings.inject([]) do |result,(product_id,predicted_rating)|
        result << {:user_id => user.id, :algorithm => 'profile', :product_id => product_id, :predicted_rating => predicted_rating }
      end
    end

  end

  module ItemBased

    def self.recommendations_for(user,options = {}) 
      defaults = {:limit => 8}
      options = defaults.merge options
      rated_product_ids = user.rated_product_ids
      return [] if rated_product_ids.empty? 
      totals  = {}
      totals.default= 0.0
      similarity_sum = {}
      similarity_sum.default= 0.0
      
      candidates = Rating.find(:all,:select => 'DISTINCT product_id',:conditions => ['product_id NOT IN (?)',rated_product_ids])
                                                    
      rated_product_ids.each do |product_id|
        candidates.each do |candidate|   
          similarity = Rails.cache.fetch("products_sim_distance/#{[product_id,candidate.product_id].map(&:to_i).sort.join('/')}") do 
            Recommender.sim_distance(product_id,candidate.product_id)
          end
          similarity_sum[candidate.product_id] += similarity
          totals[candidate.product_id] +=  user.rate_for(product_id).to_f * similarity    
        end
      end   
      
      rankings = {}
      totals.each_pair do |product_id,total|
        recommendation_score =  (total/similarity_sum[product_id])
        rankings[product_id] = recommendation_score
      end
      ids = rankings.sort{|x,y| y.second <=> x.second }.map(&:first) [0,options[:limit]]
      predicted_ratings = rankings.select{ |k,v| ids.include?(k) }
      predicted_ratings.inject([]) do |result,(product_id,predicted_rating)|
        result << {:user_id => user.id, :algorithm => 'item', :product_id => product_id, :predicted_rating => predicted_rating }
      end.sort{|x,y| y[:predicted_rating] <=> x[:predicted_rating] }
    end

  end

  module TrustBased
    
    def self.recommendations_for(user,options = {})
      defaults = {:limit => 8}
      options = defaults.merge options

      totals  = {}
      totals.default= 0.0
      similarity_sum = {}
      similarity_sum.default= 0.0

      self.trusted_users(user) do |other,similarity|                         
        # Isso me parace um workarround de um bug do rails!                        
        ids = user.rated_product_ids.empty? ? false  : user.rated_product_ids
        ratings = Rating.find :all, :conditions => ['user_id = ? and product_id NOT IN (?)',other,ids]
        ratings.each do |rating|
          totals[rating.product_id] += (rating.stars.to_f * similarity)
          similarity_sum[rating.product_id] += similarity
        end
      end
      rankings = {}
      totals.each_pair do |product_id,total|
        recommendation_score =  (total/similarity_sum[product_id])
        rankings[product_id] = recommendation_score
      end
      ids = rankings.sort{|x,y| y.second <=> x.second }.map(&:first) [0,options[:limit]]
      predicted_ratings = rankings.select{ |k,v| ids.include?(k) }
      predicted_ratings.inject([]) do |result,(product_id,predicted_rating)|
        result << {:user_id => user.id, :algorithm => 'trust', :product_id => product_id, :predicted_rating => predicted_rating }
      end.sort{|x,y| y[:predicted_rating] <=> x[:predicted_rating] }
    end
    
    def self.trusted_users(user, options = {})
      defaults = { :min_trust => 0.0 }
      options = defaults.merge(options)
      trusted_users = []
      user.recommenders.each do |other|
        next if other == user
        trust = self.trust(user,other)
        next if trust <= options[:min_trust]
        trusted_users << other
        yield other,trust if block_given?
      end                     
      trusted_users
    end
    
    def self.trust(user,other_user)
      products_ids = UserRecommendation.find(:all,:conditions => {:sender_id => other_user, :target_id => user}).map(&:product_id)
      return 0 if products_ids.empty?
      Rating.average('(stars - 3.0)/2.0',:conditions => {:user_id => user, :product_id => products_ids}) || 0
    end
    
  end
  
end
